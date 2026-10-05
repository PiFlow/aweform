"""D-060 V0.5 endpoint-only round interior-obstacle substrate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

import gymnasium as gym
import numpy as np

from .body import Body, Coordinate
from .d045 import (
    D045_AMBIENT_TEMPERATURE_C, D045_BATTERY_CAPACITY_J,
    D045_INITIAL_BATTERY_J, D045_MAX_WHEEL_DELTA_RAD,
    D045_WHEEL_RADIUS_METRES, D045_WHEEL_TRACK_WIDTH_METRES,
    D045ChargePhase, D045Observation, D045PhysicalConfig,
    D045TransitionTelemetry, _action_pair, _ChargeDecision,
    _coordinate_option, _float_option, _termination_reason,
    integrate_differential_drive, quantize_wheel_delta, wheel_effort,
)
from .d058 import D058ContactTelemetry, D058Env, D058PhysicalConfig

PROTOCOL_VERSION: Final = "d060-v05-round-interior-obstacle-substrate-v1"
ARTIFACT_SCHEMA_VERSION: Final = "D060-1"
BASE_SHA: Final = "e11ad91b3b7c649185bd1298ad5f3a791be571f8"
TAU_C: Final = 1.0e-12
A: Final = 0.090
C: Final = 0.1075
R_H: Final = math.hypot(A, C)
ROOM_SIDE_M: Final = 3.0

# (id, primitive, geometry, radius); arc geometry is (cx,cy,r0,a0,a1),
# segment geometry is (ax,ay,bx,by), and post geometry is (x,y).
FROZEN_LAYOUT: Final = (
    ("A1", "arc", (1.50, 2.00, 0.40, math.radians(30), math.radians(150)), 0.025),
    ("A2", "arc", (2.75, 1.50, 0.40, math.radians(135), math.radians(225)), 0.025),
    ("A3", "arc", (0.40, 2.60, 0.40, math.radians(270), math.radians(360)), 0.025),
    ("S1", "segment", (1.175, 0.55, 1.825, 0.55), 0.025),
    ("S2", "segment", (0.55, 1.10, 0.55, 1.75), 0.025),
    ("P1", "post", (2.35, 0.60), 0.05),
    ("P2", "post", (2.45, 2.45), 0.05),
)


@dataclass(frozen=True, slots=True)
class D060PhysicalConfig:
    """Fixed 3 m S2 room; all physical values are inherited from D-045."""
    room_side_m: float = ROOM_SIDE_M
    _base: D045PhysicalConfig = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if isinstance(self.room_side_m, bool) or self.room_side_m != ROOM_SIDE_M:
            raise ValueError("room_side_m must be exactly 3.0")
        object.__setattr__(self, "_base", D045PhysicalConfig(
            world_min=(0.0, 0.0), world_max=(ROOM_SIDE_M, ROOM_SIDE_M)))

    def __getattr__(self, name: str) -> Any:
        if name in ("world_min", "world_max"):
            raise AttributeError(name)
        return getattr(self._base, name)


@dataclass(frozen=True, slots=True)
class D060ObstacleContact:
    obstacle_id: str
    primitive: str
    p_room: Coordinate
    p_exec: Coordinate
    push_out_vector: Coordinate
    push_out_magnitude_m: float
    unconstrained_gap_m: float
    active_features: tuple[tuple[str, str], ...]
    active_contact_count: int
    residual_m: float


@dataclass(frozen=True, slots=True)
class D060StepContact:
    unconstrained_endpoint: Coordinate
    executed_endpoint: Coordinate
    resolved_by: str
    removed_displacement: Coordinate
    removed_displacement_magnitude_m: float


def _vertices(p: Coordinate, theta: float) -> tuple[Coordinate, ...]:
    co, si = math.cos(theta), math.sin(theta)
    return tuple((p[0] + sx*A*co - sy*C*si,
                  p[1] + sx*A*si + sy*C*co)
                 for sx, sy in ((-1.,-1.),(1.,-1.),(1.,1.),(-1.,1.)))


def _point_segment(p: Coordinate, a: Coordinate, b: Coordinate) -> float:
    dx, dy = b[0]-a[0], b[1]-a[1]
    den = dx*dx+dy*dy
    t = 0.0 if den == 0 else min(1., max(0., ((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den))
    return math.hypot(p[0]-a[0]-t*dx, p[1]-a[1]-t*dy)


def _segments_cross(a: Coordinate, b: Coordinate, c: Coordinate, d: Coordinate) -> bool:
    """Exact closed-segment intersection, including bounded collinear overlap."""
    def orient(p, q, r):
        return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    def on_segment(p, q, r):
        return (min(p[0], q[0]) <= r[0] <= max(p[0], q[0])
                and min(p[1], q[1]) <= r[1] <= max(p[1], q[1]))
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    if o1 == 0 and on_segment(a, b, c): return True
    if o2 == 0 and on_segment(a, b, d): return True
    if o3 == 0 and on_segment(c, d, a): return True
    if o4 == 0 and on_segment(c, d, b): return True
    return (o1 < 0 < o2 or o2 < 0 < o1) and (o3 < 0 < o4 or o4 < 0 < o3)


def _inside_polygon(q: Coordinate, vertices: tuple[Coordinate,...]) -> bool:
    signs=[]
    for i,a in enumerate(vertices):
        b=vertices[(i+1)%len(vertices)]
        signs.append((b[0]-a[0])*(q[1]-a[1])-(b[1]-a[1])*(q[0]-a[0]))
    return all(x>=0 for x in signs) or all(x<=0 for x in signs)


def _angle_on_sweep(theta: float, a0: float, a1: float) -> bool:
    while theta < a0: theta += 2*math.pi
    return theta <= a1


def _curve_distance(q: Coordinate, obstacle: tuple[str,str,tuple[float,...],float]) -> tuple[float,str]:
    _, kind, g, _ = obstacle
    if kind == "post": return math.hypot(q[0]-g[0],q[1]-g[1]), "centre-line"
    if kind == "segment":
        a=(g[0],g[1]); b=(g[2],g[3])
        return _point_segment(q,a,b), "centre-line"
    cx,cy,r,a0,a1=g
    angle=math.atan2(q[1]-cy,q[0]-cx)
    if _angle_on_sweep(angle,a0,a1): return abs(math.hypot(q[0]-cx,q[1]-cy)-r), "arc"
    e0=(cx+r*math.cos(a0),cy+r*math.sin(a0)); e1=(cx+r*math.cos(a1),cy+r*math.sin(a1))
    return min((math.dist(q,e0),"cap-start"),(math.dist(q,e1),"cap-end"))


def _gap(p: Coordinate, theta: float, obstacle: tuple[str,str,tuple[float,...],float]) -> float:
    """Signed clearance via rectangle feature distance to centre-line."""
    verts=_vertices(p,theta)
    distances=[_curve_distance(v,obstacle)[0] for v in verts]
    for i in range(4):
        a,b=verts[i],verts[(i+1)%4]
        kind=obstacle[1]; g=obstacle[2]
        if kind == "post":
            if _inside_polygon((g[0],g[1]),verts): return -obstacle[3]
            targets=((g[0],g[1]),)
        elif kind == "segment":
            sa,sb=(g[0],g[1]),(g[2],g[3])
            if _inside_polygon(sa,verts) or _inside_polygon(sb,verts): return -obstacle[3]
            if any(_segments_cross(sa,sb,verts[j],verts[(j+1)%4]) for j in range(4)): return -obstacle[3]
            targets=(sa,sb)
        else:
            cx,cy,r,a0,a1=g
            candidates=[]
            # Closest point on this edge to the arc centre; radial surface point
            dx,dy=b[0]-a[0],b[1]-a[1]; den=dx*dx+dy*dy
            t=min(1.,max(0.,((cx-a[0])*dx+(cy-a[1])*dy)/den))
            foot=(a[0]+t*dx,a[1]+t*dy)
            ang=math.atan2(foot[1]-cy,foot[0]-cx)
            if _angle_on_sweep(ang,a0,a1) and math.dist(foot,(cx,cy)):
                rr=math.dist(foot,(cx,cy)); candidates.append((cx+r*(foot[0]-cx)/rr,cy+r*(foot[1]-cy)/rr))
            candidates.extend(((cx+r*math.cos(a0),cy+r*math.sin(a0)),(cx+r*math.cos(a1),cy+r*math.sin(a1))))
            targets=tuple(candidates)
        for q in targets: distances.append(_point_segment(q,a,b))
    if obstacle[1] == "arc":
        # Intersect each rectangle edge with the finite circular sweep.
        cx,cy,r0,a0,a1=obstacle[2]
        for i in range(4):
            a,b=verts[i],verts[(i+1)%4]; dx,dy=b[0]-a[0],b[1]-a[1]
            fx,fy=a[0]-cx,a[1]-cy; aa=dx*dx+dy*dy; bb=2*(fx*dx+fy*dy); cc=fx*fx+fy*fy-r0*r0
            disc=bb*bb-4*aa*cc
            if disc>=0:
                for t in ((-bb-math.sqrt(disc))/(2*aa),(-bb+math.sqrt(disc))/(2*aa)):
                    if 0<=t<=1 and _angle_on_sweep(math.atan2(a[1]+t*dy-cy,a[0]+t*dx-cx),a0,a1): return -obstacle[3]
    return min(distances)-obstacle[3]


def _edge_centerline_distance(a:Coordinate,b:Coordinate,obstacle)->float:
    kind,g=obstacle[1],obstacle[2]
    if kind=="post":return _point_segment((g[0],g[1]),a,b)
    if kind=="segment":
        c,d=(g[0],g[1]),(g[2],g[3])
        if _segments_cross(a,b,c,d):return 0.
        return min(_point_segment(a,c,d),_point_segment(b,c,d),_point_segment(c,a,b),_point_segment(d,a,b))
    cx,cy,r0,a0,a1=g
    best=min(_curve_distance(a,obstacle)[0],_curve_distance(b,obstacle)[0])
    for angle in (a0,a1):
        endpoint=(cx+r0*math.cos(angle),cy+r0*math.sin(angle))
        best=min(best,_point_segment(endpoint,a,b))
    dx,dy=b[0]-a[0],b[1]-a[1]; den=dx*dx+dy*dy
    t=min(1.,max(0.,((cx-a[0])*dx+(cy-a[1])*dy)/den)); foot=(a[0]+t*dx,a[1]+t*dy)
    ang=math.atan2(foot[1]-cy,foot[0]-cx)
    if _angle_on_sweep(ang,a0,a1):best=min(best,abs(math.dist(foot,(cx,cy))-r0))
    # An edge can cross the circle at a point on the finite angular sweep.
    fx,fy=a[0]-cx,a[1]-cy; aa=den; bb=2*(fx*dx+fy*dy); cc=fx*fx+fy*fy-r0*r0; disc=bb*bb-4*aa*cc
    if disc>=0:
        for t in ((-bb-math.sqrt(disc))/(2*aa),(-bb+math.sqrt(disc))/(2*aa)):
            if 0<=t<=1 and _angle_on_sweep(math.atan2(a[1]+t*dy-cy,a[0]+t*dx-cx),a0,a1):return 0.
    return best


def _closest_centerline_point(p: Coordinate, obstacle):
    """Return the closest centre-line point and its normative obstacle feature."""
    _,kind,g,_=obstacle
    if kind=="post": return (g[0],g[1]),"centre-line"
    if kind=="segment":
        a,b=(g[0],g[1]),(g[2],g[3]); dx,dy=b[0]-a[0],b[1]-a[1]
        t=min(1.,max(0.,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy)))
        point=(a[0]+t*dx,a[1]+t*dy)
        return point,"end-cap" if t in (0.,1.) else "centre-line"
    cx,cy,r0,a0,a1=g; dx,dy=p[0]-cx,p[1]-cy; length=math.hypot(dx,dy)
    angle=math.atan2(dy,dx)
    if length and _angle_on_sweep(angle,a0,a1):
        point=(cx+r0*dx/length,cy+r0*dy/length)
        return point,"outer-surface" if length>r0 else "inner-surface"
    ends=((cx+r0*math.cos(a0),cy+r0*math.sin(a0)),(cx+r0*math.cos(a1),cy+r0*math.sin(a1)))
    return min(ends,key=lambda q:(math.dist(p,q),q[0],q[1])),"end-cap"


def _segment_closest_pair(a: Coordinate,b: Coordinate,c: Coordinate,d: Coordinate):
    if _segments_cross(a,b,c,d):
        def cross(p,q,r): return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
        den=(b[0]-a[0])*(d[1]-c[1])-(b[1]-a[1])*(d[0]-c[0])
        if den:
            t=((c[0]-a[0])*(d[1]-c[1])-(c[1]-a[1])*(d[0]-c[0]))/den
            point=(a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1]))
            return point,point
        shared=sorted({p for p in (a,b,c,d) if _point_segment(p,a,b)==0. and _point_segment(p,c,d)==0.})
        point=shared[0]
        return point,point
    candidates=[]
    for p in (a,b):
        q=_closest_on_segment(p,c,d); candidates.append((math.dist(p,q),p,q))
    for q in (c,d):
        p=_closest_on_segment(q,a,b); candidates.append((math.dist(p,q),p,q))
    _,p,q=min(candidates,key=lambda x:(x[0],x[1][0],x[1][1],x[2][0],x[2][1]))
    return p,q


def _closest_on_segment(p: Coordinate,a: Coordinate,b: Coordinate)->Coordinate:
    dx,dy=b[0]-a[0],b[1]-a[1]; den=dx*dx+dy*dy
    t=0. if den==0 else min(1.,max(0.,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den))
    return a[0]+t*dx,a[1]+t*dy


def _edge_contact_witness(a: Coordinate,b: Coordinate,obstacle):
    """Return closest hull/centre-line witnesses and normative obstacle feature."""
    _,kind,g,_=obstacle
    if kind=="post":
        centre=(g[0],g[1]); return _closest_on_segment(centre,a,b),centre,"centre-line"
    if kind=="segment":
        hull,centre=_segment_closest_pair(a,b,(g[0],g[1]),(g[2],g[3]))
        feature="end-cap" if centre in ((g[0],g[1]),(g[2],g[3])) else "centre-line"
        return hull,centre,feature
    cx,cy,r0,a0,a1=g; candidates=[]
    for hull in (a,b):
        centre,feature=_closest_centerline_point(hull,obstacle)
        candidates.append((math.dist(hull,centre),hull,centre,feature))
    for angle in (a0,a1):
        centre=(cx+r0*math.cos(angle),cy+r0*math.sin(angle)); hull=_closest_on_segment(centre,a,b)
        candidates.append((math.dist(hull,centre),hull,centre,"end-cap"))
    foot=_closest_on_segment((cx,cy),a,b); dx,dy=foot[0]-cx,foot[1]-cy; length=math.hypot(dx,dy)
    if length:
        centre=(cx+r0*dx/length,cy+r0*dy/length); angle=math.atan2(centre[1]-cy,centre[0]-cx)
        if _angle_on_sweep(angle,a0,a1):
            hull=_closest_on_segment(centre,a,b)
            candidates.append((math.dist(hull,centre),hull,centre,"outer-surface" if math.dist(hull,(cx,cy))>r0 else "inner-surface"))
    dx,dy=b[0]-a[0],b[1]-a[1]; fx,fy=a[0]-cx,a[1]-cy
    aa=dx*dx+dy*dy; bb=2*(fx*dx+fy*dy); cc=fx*fx+fy*fy-r0*r0; disc=bb*bb-4*aa*cc
    if disc>=0 and aa:
        for t in ((-bb-math.sqrt(disc))/(2*aa),(-bb+math.sqrt(disc))/(2*aa)):
            if 0<=t<=1:
                point=(a[0]+t*dx,a[1]+t*dy); angle=math.atan2(point[1]-cy,point[0]-cx)
                if _angle_on_sweep(angle,a0,a1):
                    candidates.append((0.,point,point,"outer-surface" if math.dist(point,(cx,cy))>r0 else "inner-surface"))
    _,hull,centre,feature=min(candidates,key=lambda x:(x[0],x[1][0],x[1][1],x[2][0],x[2][1],x[3]))
    return hull,centre,feature


def _obstacle_boundary_witness(hull: Coordinate,centre: Coordinate,radius: float)->Coordinate:
    distance=math.dist(hull,centre)
    if distance==0.: raise RuntimeError("contact witness has undefined obstacle-boundary direction")
    return centre[0]+radius*(hull[0]-centre[0])/distance,centre[1]+radius*(hull[1]-centre[1])/distance


def _canonicalize_contact_witnesses(measured):
    """Merge shared closed-feature witnesses only under exact geometric equality."""
    canonical=[]
    for contact in measured:
        if contact["hull_feature"].startswith("edge-") and any(
            other["hull_feature"].startswith("vertex-")
            and contact["hull_witness"]==other["hull_witness"]
            and contact["boundary_witness"]==other["boundary_witness"]
            and contact["obstacle_feature"]==other["obstacle_feature"]
            for other in canonical
        ):
            continue
        canonical.append(contact)
    return tuple(canonical)


def _active_contact_witnesses(p: Coordinate,theta: float,obstacle):
    """Measure active pairs and merge only exactly equal physical witnesses."""
    vertices=_vertices(p,theta); measured=[]
    for j,vertex in enumerate(vertices):
        centre,feature=_closest_centerline_point(vertex,obstacle)
        distance=math.dist(vertex,centre)
        if abs(distance-obstacle[3])<=TAU_C:
            measured.append({"hull_feature":f"vertex-{j}","obstacle_feature":feature,
                             "hull_witness":vertex,"centre_witness":centre,
                             "boundary_witness":_obstacle_boundary_witness(vertex,centre,obstacle[3]),
                             "distance_m":distance,"residual_m":distance-obstacle[3]})
    for j in range(4):
        a,b=vertices[j],vertices[(j+1)%4]
        hull,centre,feature=_edge_contact_witness(a,b,obstacle)
        distance=math.dist(hull,centre)
        if abs(distance-obstacle[3])<=TAU_C:
            measured.append({"hull_feature":f"edge-{j}","obstacle_feature":feature,
                             "hull_witness":hull,"centre_witness":centre,
                             "boundary_witness":_obstacle_boundary_witness(hull,centre,obstacle[3]),
                             "distance_m":distance,"residual_m":distance-obstacle[3]})
    return tuple(measured),_canonicalize_contact_witnesses(measured)


def _curves(theta: float, obstacle: tuple[str,str,tuple[float,...],float]):
    """Finite C.1 curve list: line (normal,offset) and circle (center,radius)."""
    ident,kind,g,r=obstacle; vs=_vertices((0.,0.),theta); out=[]
    def line(n,offset):
        norm=math.hypot(*n)
        if norm: out.append(("line",(n[0]/norm,n[1]/norm),offset/norm))
    def circle(cen,rad):
        if rad >= 0: out.append(("circle",cen,rad))
    # Four hull vertices and four edges.
    for v in vs:
        if kind == "post": circle((g[0]-v[0],g[1]-v[1]),r)
        elif kind == "segment":
            circle((g[0]-v[0],g[1]-v[1]),r); circle((g[2]-v[0],g[3]-v[1]),r)
            dx,dy=g[2]-g[0],g[3]-g[1]; le=math.hypot(dx,dy); n=(-dy/le,dx/le)
            for sign in (-1.,1.): line(n,n[0]*(g[0]-v[0])+n[1]*(g[1]-v[1])+sign*r)
        else:
            cx,cy,r0,a0,a1=g
            for a in (a0,a1):
                k=(cx+r0*math.cos(a),cy+r0*math.sin(a)); circle((k[0]-v[0],k[1]-v[1]),r)
            circle((cx-v[0],cy-v[1]),r0-r); circle((cx-v[0],cy-v[1]),r0+r)
    for i in range(4):
        v,w=vs[i],vs[(i+1)%4]; edge=(w[0]-v[0],w[1]-v[1]); le=math.hypot(*edge); n=(edge[1]/le,-edge[0]/le)
        h=n[0]*v[0]+n[1]*v[1]
        if kind == "post":
            line(n,n[0]*g[0]+n[1]*g[1]-h-r)
        elif kind == "segment":
            for k in ((g[0],g[1]),(g[2],g[3])): line(n,n[0]*k[0]+n[1]*k[1]-h-r)
        else:
            cx,cy,r0,_,_=g
            line(n,n[0]*cx+n[1]*cy-h-r0-r)
            for a in (g[3],g[4]):
                k=(cx+r0*math.cos(a),cy+r0*math.sin(a)); line(n,n[0]*k[0]+n[1]*k[1]-h-r)
    return out


def _intersections(c1,c2):
    t1,a1,b1=c1; t2,a2,b2=c2
    if t1==t2=="line":
        det=a1[0]*a2[1]-a1[1]*a2[0]
        if det == 0: return ()
        return (((b1*a2[1]-a1[1]*b2)/det,(a1[0]*b2-b1*a2[0])/det),)
    if t1=="line": return _intersections(c2,c1)
    if t1=="circle" and t2=="line":
        (cx,cy),r=a1,b1; n=a2; d=b2-(n[0]*cx+n[1]*cy)
        if abs(d)>r: return ()
        foot=(cx+d*n[0],cy+d*n[1]); h=math.sqrt(max(0.,r*r-d*d)); tangent=(-n[1],n[0])
        return ((foot[0]+h*tangent[0],foot[1]+h*tangent[1]),(foot[0]-h*tangent[0],foot[1]-h*tangent[1]))
    (x1,y1),r1=a1,b1; (x2,y2),r2=a2,b2; dx,dy=x2-x1,y2-y1; d=math.hypot(dx,dy)
    if d==0 or d>r1+r2 or d<abs(r1-r2): return ()
    q=(r1*r1-r2*r2+d*d)/(2*d); h=math.sqrt(max(0.,r1*r1-q*q)); ux,uy=dx/d,dy/d
    x,y=x1+q*ux,y1+q*uy
    return ((x-h*uy,y+h*ux),(x+h*uy,y-h*ux))


def _project(p: Coordinate,theta: float,obstacle):
    curves=_curves(theta,obstacle); candidates=[]; in_bound=[]
    for i,(typ,a,b) in enumerate(curves):
        if typ=="line":
            d=b-(a[0]*p[0]+a[1]*p[1]); candidates.append(((p[0]+d*a[0],p[1]+d*a[1]),f"curve[{i}]-nearest"))
        else:
            (cx,cy),rad=a,b; dx,dy=p[0]-cx,p[1]-cy; length=math.hypot(dx,dy)
            if length:
                candidates.extend((((cx+rad*dx/length,cy+rad*dy/length),f"curve[{i}]-radial+"),((cx-rad*dx/length,cy-rad*dy/length),f"curve[{i}]-radial-")))
            else: candidates.extend((((cx+rad,cy),f"curve[{i}]-zero+"),((cx-rad,cy),f"curve[{i}]-zero-")))
    for i,c1 in enumerate(curves):
        for j,c2 in enumerate(curves[i+1:],i+1):
            candidates.extend((q,f"pair[{i},{j}]") for q in _intersections(c1,c2))
    # ADR-0020 Lemma 2 permits discarding only candidates outside this bound.
    bound=R_H+obstacle[3]+TAU_C; accepted=[]
    for q,source in candidates:
        if not all(math.isfinite(value) for value in q):
            raise RuntimeError(f"uncomputable projection candidate {source}: {q!r}")
        distance=math.dist(p,q)
        if distance>bound: continue
        gap=_gap(q,theta,obstacle)
        if not math.isfinite(gap):
            raise RuntimeError(f"uncomputable projection gap for {source}: point={q!r}")
        item={"source":source,"point":q,"distance_m":distance,"gap_m":gap}
        in_bound.append(item)
        if gap>=-TAU_C: accepted.append((q,source,distance,gap))
    if not accepted: raise RuntimeError(f"no accepted finite projection candidate for {obstacle[0]}; in-bound candidates={in_bound!r}")
    accepted.sort(key=lambda item:(item[2],item[0][0],item[0][1]))
    q=accepted[0][0]
    measured,canonical=_active_contact_witnesses(q,theta,obstacle)
    active=tuple((item["hull_feature"],item["obstacle_feature"]) for item in canonical)
    if not 1<=len(active)<=2:
        raise RuntimeError(f"projection has {len(active)} distinct reconstructible active features for {obstacle[0]}; measured={measured!r}; canonical={canonical!r}; selected={accepted[0]!r}; in-bound candidates={in_bound!r}")
    return q,max(0.,-_gap(q,theta,obstacle)),active,len(active)


class D060Env(gym.Env[np.ndarray,np.ndarray]):
    metadata: dict[str,object]={"render_modes":[]}
    def __init__(self,config:D060PhysicalConfig|None=None):
        self.config=config or D060PhysicalConfig()
        self.action_space=gym.spaces.Box(low=np.full(2,-D045_MAX_WHEEL_DELTA_RAD),high=np.full(2,D045_MAX_WHEEL_DELTA_RAD),dtype=np.float64)
        self.observation_space=gym.spaces.Box(low=np.asarray((0,0,0,0,0,0,-D045_MAX_WHEEL_DELTA_RAD,-D045_MAX_WHEEL_DELTA_RAD),dtype=np.float32),high=np.asarray((1,1,1,1,1,1,D045_MAX_WHEEL_DELTA_RAD,D045_MAX_WHEEL_DELTA_RAD),dtype=np.float32),dtype=np.float32)
        self.body:Body|None=None; self.station_center:Coordinate|None=None; self.body_temperature_c:float|None=None
        self._battery_j=0.; self._charger_termination_latched=False; self._previous_wheel_delta=(0.,0.); self._step_count=0; self._episode_done=True
        self.last_room_stage:D058ContactTelemetry|None=None; self.last_obstacle_stage:D060ObstacleContact|None=None; self.last_step_contact:D060StepContact|None=None
        self.last_transition:D045TransitionTelemetry|None=None
    @property
    def battery_j(self): return self._battery_j
    @property
    def charger_termination_latched(self): return self._charger_termination_latched
    @property
    def charging_contact(self):
        if self.body is None or self.station_center is None: raise RuntimeError("environment must be reset before observing")
        from .d045 import _dock_contact
        return _dock_contact(self.body.position,self.body.heading,self.station_center,self.config._base)[0]
    def _extent(self,heading): return A*abs(math.cos(heading))+C*abs(math.sin(heading)), A*abs(math.sin(heading))+C*abs(math.cos(heading))
    def _legal(self,p,theta): return all(_gap(p,theta,o)>=0. for o in FROZEN_LAYOUT) and (lambda h: h[0]<=p[0]<=3-h[0] and h[1]<=p[1]<=3-h[1])(self._extent(theta))
    def reset(self,*,seed:int|None=None,options:dict[str,object]|None=None):
        super().reset(seed=seed); setup=options or {}; allowed={"body_position","station_center","heading","battery_j","body_temperature_c","charger_termination_latched"}
        unknown=set(setup)-allowed
        if unknown: raise ValueError(f"unknown reset option(s): {sorted(unknown)}")
        p=_coordinate_option(setup,"body_position",(.75,.75)); station=_coordinate_option(setup,"station_center",(1.5,1.5))
        if station!=(1.5,1.5): raise ValueError("station_center must equal (1.5, 1.5)")
        theta=_float_option("heading",setup.get("heading",0.)); battery=_float_option("battery_j",setup.get("battery_j",D045_INITIAL_BATTERY_J)); temp=_float_option("body_temperature_c",setup.get("body_temperature_c",D045_AMBIENT_TEMPERATURE_C)); latched=setup.get("charger_termination_latched",False)
        if not isinstance(latched,bool): raise ValueError("charger_termination_latched must be a bool")
        if not 0<=battery<=D045_BATTERY_CAPACITY_J: raise ValueError("battery_j must be within battery capacity")
        hx,hy=self._extent(theta)
        if not(hx<=p[0]<=3-hx and hy<=p[1]<=3-hy): raise ValueError("body_position hull must be fully inside the room")
        gaps=tuple(_gap(p,theta,o) for o in FROZEN_LAYOUT)
        if any(g<0 for g in gaps): raise ValueError("body_position hull penetrates an obstacle")
        self.body=Body(x=p[0],y=p[1],heading=theta,energy=0.); self.station_center=station; self.body_temperature_c=temp; self._battery_j=battery; self._charger_termination_latched=latched; self._previous_wheel_delta=(0.,0.); self._step_count=0; self._episode_done=False
        self.last_room_stage=self.last_obstacle_stage=self.last_step_contact=self.last_transition=None
        return self._observation().as_array(),{}
    def _observation(self):
        if self.body is None or self.station_center is None or self.body_temperature_c is None: raise RuntimeError("environment must be reset before observing")
        from .exp003 import sample_directional_beacon
        beacon=sample_directional_beacon(self.body,self.station_center,probe_distance=self.config.beacon_probe_distance_m,sensor_angle=self.config.beacon_sensor_angle_rad,beacon_scale=self.config.beacon_scale_m)
        clamp=lambda x,l,h:min(max(x,l),h)
        return D045Observation(energy_normalized=clamp(self._battery_j/self.config.battery_capacity_j,0.,1.),temperature_normalized=clamp((self.body_temperature_c-self.config.visible_temperature_min_c)/(self.config.visible_temperature_max_c-self.config.visible_temperature_min_c),0.,1.),beacon_left=beacon.left,beacon_forward=beacon.forward,beacon_right=beacon.right,charging_contact=self.charging_contact,wheel_delta_left=quantize_wheel_delta(self._previous_wheel_delta[0],self.config.encoder_quantum_rad),wheel_delta_right=quantize_wheel_delta(self._previous_wheel_delta[1],self.config.encoder_quantum_rad))
    def step(self,action):
        if self._episode_done: raise RuntimeError("episode is over; call reset() before step()")
        req_l,req_r=_action_pair(action)
        if self.body is None or self.station_center is None or self.body_temperature_c is None: raise RuntimeError("environment must be reset before step()")
        cfg=self.config._base; m=D045_MAX_WHEEL_DELTA_RAD; left=min(max(req_l,-m),m); right=min(max(req_r,-m),m); p0=self.body.position; t0=self.body.heading
        pfull,tfull=integrate_differential_drive(p0,t0,left,right,track_width_m=cfg.wheel_track_width_m,wheel_radius_m=cfg.wheel_radius_m)
        hx,hy=self._extent(tfull); L=3.; proom=(min(max(pfull[0],hx),L-hx),min(max(pfull[1],hy),L-hy)); pushing=(pfull[0]<hx,pfull[0]>L-hx,pfull[1]<hy,pfull[1]>L-hy); removed=math.dist(pfull,proom)
        room=D058ContactTelemetry(pfull,proom,*pushing,hx,hy,removed,removed)
        violations=[(i,_gap(pfull,tfull,o)) for i,o in enumerate(FROZEN_LAYOUT) if _gap(pfull,tfull,o)<0.]
        room_bad=any(pushing)
        if len(violations)+int(room_bad)>1: raise RuntimeError("more than one room/obstacle constraint violated")
        obstacle_contact=None; pexec=proom; resolved="room" if room_bad else "none"
        if violations:
            idx,gap=violations[0]; ob=FROZEN_LAYOUT[idx]; pexec,resid,features,nactive=_project(pfull,tfull,ob)
            obstacle_contact=D060ObstacleContact(ob[0],ob[1],pfull,pexec,(pexec[0]-pfull[0],pexec[1]-pfull[1]),math.dist(pexec,pfull),gap,features,min(2,nactive),resid); resolved="obstacle"
        if not(self._extent(tfull)[0]<=pexec[0]<=3-self._extent(tfull)[0] and self._extent(tfull)[1]<=pexec[1]<=3-self._extent(tfull)[1]) or any(_gap(pexec,tfull,o)<-TAU_C for o in FROZEN_LAYOUT): raise AssertionError("executed endpoint is illegal")
        battery_before,temp_before=self._battery_j,self.body_temperature_c; contact_before=self.charging_contact; self.body.x,self.body.y,self.body.heading=pexec[0],pexec[1],tfull
        from .d045 import _dock_contact
        contact_after,plus_err,minus_err=_dock_contact(pexec,tfull,self.station_center,cfg); effort=wheel_effort(left,right,m); actuator_power=cfg.wheel_power_scale_w*effort; actuator_heat=cfg.wheel_body_heat_scale_w*effort; total_load=cfg.electronics_power_w+actuator_power; load_energy=total_load*cfg.dt_seconds; charge=self._charge_decision(contact_after,battery_before)
        charge_energy=min(charge.requested_stored_power_w*cfg.dt_seconds,max(0.,cfg.battery_capacity_j-battery_before+load_energy)); stored=charge_energy/cfg.dt_seconds; battery_after=min(cfg.battery_capacity_j,max(0.,battery_before+charge_energy-load_energy)); latched=charge.termination_latched_after
        if charge.phase in (D045ChargePhase.BULK,D045ChargePhase.TAPER_1,D045ChargePhase.TAPER_2) and battery_after>=cfg.battery_capacity_j: latched=True
        charger_input=stored/cfg.charge_efficiency if stored>0 else 0.; charging_heat=charger_input-stored if stored>0 else 0.; total_heat=cfg.electronics_body_heat_w+actuator_heat+charging_heat; exchange=cfg.thermal_conductance_w_per_k*(cfg.ambient_temperature_c-temp_before); temp_after=temp_before+cfg.dt_seconds*(total_heat+exchange)/cfg.thermal_capacitance_j_per_k
        self._battery_j,self.body_temperature_c,self._charger_termination_latched=battery_after,temp_after,latched; energy_bad=battery_after<=0.; protective=temp_after>=cfg.protective_temperature_c and temp_after<cfg.hard_temperature_c; emergency=temp_after>=cfg.hard_temperature_c; reason=_termination_reason(emergency,protective,energy_bad); terminated=reason is not None; self._step_count+=1; truncated=not terminated and self._step_count>=cfg.episode_horizon; self._episode_done=terminated or truncated; self._previous_wheel_delta=(left,right)
        self.last_room_stage=room; self.last_obstacle_stage=obstacle_contact; self.last_step_contact=D060StepContact(pfull,pexec,resolved,(pexec[0]-pfull[0],pexec[1]-pfull[1]),math.dist(pfull,pexec))
        self.last_transition=D045TransitionTelemetry(step_index=self._step_count,requested_delta_left=req_l,requested_delta_right=req_r,clamped_delta_left=left,clamped_delta_right=right,actual_delta_left=left,actual_delta_right=right,boundary_scale=1.0,position_before=p0,position_after=pexec,heading_before=t0,heading_after=tfull,station_center=self.station_center,charging_contact_before=contact_before,charging_contact_after=contact_after,dock_plus_error_m=plus_err,dock_minus_error_m=minus_err,battery_before_j=battery_before,battery_after_j=battery_after,body_temperature_before_c=temp_before,body_temperature_after_c=temp_after,actuator_electrical_power_w=actuator_power,electronics_electrical_power_w=cfg.electronics_power_w,total_electrical_load_w=total_load,charge_phase=charge.phase,requested_stored_power_w=charge.requested_stored_power_w,actual_stored_power_w=stored,charger_input_power_w=charger_input,charging_body_heat_w=charging_heat,actuator_body_heat_w=actuator_heat,electronics_body_heat_w=cfg.electronics_body_heat_w,environmental_exchange_power_w=exchange,charger_termination_latched_after=latched,preferred_ceiling_crossed=temp_before<cfg.preferred_temperature_c<=temp_after,above_preferred_ceiling=temp_after>=cfg.preferred_temperature_c,energy_nonviable=energy_bad,protective_shutdown=protective,emergency_hard_shutdown=emergency,terminated=terminated,truncated=truncated,termination_reason=reason)
        return self._observation().as_array(),0.,terminated,truncated,{}
    def _charge_decision(self,contact_after,battery_before):
        cfg=self.config._base
        if not contact_after:return _ChargeDecision(D045ChargePhase.OFF,0.,False)
        soc=battery_before/cfg.battery_capacity_j
        if self._charger_termination_latched:
            if soc>cfg.resume_soc:return _ChargeDecision(D045ChargePhase.STANDBY,0.,True)
            self._charger_termination_latched=False
        if battery_before>=cfg.battery_capacity_j:return _ChargeDecision(D045ChargePhase.STANDBY,0.,True)
        if soc<cfg.bulk_soc_upper:return _ChargeDecision(D045ChargePhase.BULK,cfg.bulk_charge_power_w,False)
        if soc<cfg.taper_1_soc_upper:return _ChargeDecision(D045ChargePhase.TAPER_1,cfg.taper_1_charge_power_w,False)
        return _ChargeDecision(D045ChargePhase.TAPER_2,cfg.taper_2_charge_power_w,False)


def make_d060_env()->D060Env: return D060Env()


_D060_LAST_CASE_CONTEXT:dict[str,Any]|None=None


def _oracle_best_for_obstacle_step(env:D060Env,theta:float,obstacle:tuple[Any,...],oracle:Any,case:dict[str,Any])->tuple[float,int]:
    """Use the unified step telemetry as p_full for the independent oracle."""
    contact=env.last_obstacle_stage
    step=env.last_step_contact
    if contact is None or step is None or step.resolved_by!="obstacle":
        raise AssertionError(f"oracle requires an obstacle-resolved step case={case!r}")
    if contact.p_room!=step.unconstrained_endpoint:
        raise AssertionError(
            f"ADR-0020 §F p_room/p_full mismatch case={case!r} "
            f"reset={case.get('reset')!r} command={case.get('command')!r} "
            f"p0={case.get('p0')!r} p_full={step.unconstrained_endpoint!r} "
            f"theta_full={theta!r} contact={contact!r} step={step!r}"
        )
    return oracle.oracle_best_free_distance(step.unconstrained_endpoint,theta,obstacle)


def _h2b_requires_fresh_control(lockstep:bool,obstacle_violations:list[int])->bool:
    """H.2(b) covers obstacle-free steps after lockstep has ended."""
    return not lockstep and not obstacle_violations


def run_d060_conformance(executed_commit_sha:str|None=None)->dict[str,Any]:
    """Run ADR-0020 H.1-H.8 on the authorized deterministic evaluator matrix."""
    from collections import Counter
    from dataclasses import fields
    from . import d060_oracle as oracle
    from .d058 import _start_position as d058_start

    protected=("src/aweform/d045.py","src/aweform/d049.py","src/aweform/d050.py",
        "src/aweform/d052.py","src/aweform/d053.py","src/aweform/d054.py",
        "src/aweform/d055.py","src/aweform/d056.py","src/aweform/d057.py",
        "src/aweform/d058.py","src/aweform/d059.py","src/aweform/vis_d059.py",
        "src/aweform/development_visualizer.py","src/aweform/body.py","src/aweform/env.py",
        "src/aweform/exp001.py","src/aweform/exp003.py","src/aweform/exp003_seed_policy.py")
    protected_sha={}
    for path in protected:
        current=Path(path).read_bytes()
        base=subprocess.run(["git","show",f"{BASE_SHA}:{path}"],check=True,capture_output=True).stdout
        if current!=base: raise AssertionError(f"H.1 protected byte mismatch: {path}")
        protected_sha[path]=hashlib.sha256(current).hexdigest()
    if tuple(FROZEN_LAYOUT)!=oracle.ORACLE_LAYOUT: raise AssertionError("H.3 independent layout mismatch")

    m=D045_MAX_WHEEL_DELTA_RAD; phi=math.atan(C/A)
    headings=tuple(k*math.pi/12 for k in range(24))+(phi,math.pi-phi,math.pi+phi,2*math.pi-phi,
        math.pi/2-phi,math.pi/2+phi,3*math.pi/2-phi,3*math.pi/2+phi)
    vals=(-m,0.,m)
    u9=tuple((l,r) for l in vals for r in vals if (l,r)!=(0.,0.))+((-.565040862351,.645771823238),)
    u10=u9+((0.,0.),)
    sequences=tuple((f"Q{i+1}",tuple(cmd for _ in range(8))) for i,cmd in enumerate(u9)) + (
        ("Q10",((m,m),)*4+((m,-m),)*8),
        ("Q11",((-m,-m),)*4+((-m,m),)*8))
    rays=oracle._feature_rays()
    if len(rays)!=76 or len(headings)!=32: raise AssertionError("frozen coverage cardinality mismatch")

    wheel_delta_max=D045_WHEEL_RADIUS_METRES*m
    dtheta_max=2*D045_WHEEL_RADIUS_METRES*m/D045_WHEEL_TRACK_WIDTH_METRES
    B=2*R_H*math.sin(dtheta_max/2)+wheel_delta_max
    tau_room=64*(2.**-52)*ROOM_SIDE_M
    counters=Counter(); contact_counts=Counter(); class_counts=Counter()
    oracle_counts=Counter(); idempotence=Counter(); maxima=Counter(); attaining={}
    h6_max=Counter(); h6_case={}; h6_nonzero=Counter(); step_total=0; pocket_two=Counter()

    def opts(position,heading,battery=D045_INITIAL_BATTERY_J,temp=D045_AMBIENT_TEMPERATURE_C,latched=False):
        return {"body_position":position,"station_center":(1.5,1.5),"heading":heading,
                "battery_j":battery,"body_temperature_c":temp,"charger_termination_latched":latched}
    def transition_without_index(t):
        return tuple((f.name,getattr(t,f.name)) for f in fields(t) if f.name!="step_index")
    def compare_step(actual,control,oa,ob,ignore_index=False):
        assert actual.body.position==control.body.position and actual.body.heading==control.body.heading
        assert oa.tobytes()==ob.tobytes()
        assert actual.battery_j==control.battery_j and actual.body_temperature_c==control.body_temperature_c
        assert actual.body.energy==control.body.energy
        assert (transition_without_index(actual.last_transition)==transition_without_index(control.last_transition)) if ignore_index else actual.last_transition==control.last_transition
        assert actual.last_room_stage==control.last_contact
        assert actual.last_step_contact.executed_endpoint==control.last_contact.executed_endpoint
        assert actual.last_obstacle_stage is None
    def assert_reconstruction(env):
        room=env.last_room_stage; total=env.last_step_contact
        wall=(room.executed_endpoint[0]-room.unconstrained_endpoint[0],room.executed_endpoint[1]-room.unconstrained_endpoint[1])
        obstacle=(total.executed_endpoint[0]-room.executed_endpoint[0],total.executed_endpoint[1]-room.executed_endpoint[1])
        combined=(wall[0]+obstacle[0],wall[1]+obstacle[1])
        direct=(total.executed_endpoint[0]-total.unconstrained_endpoint[0],total.executed_endpoint[1]-total.unconstrained_endpoint[1])
        assert combined==direct
        assert not hasattr(env,"last_contact")
    def explicit_current(env):
        return opts(env.body.position,env.body.heading,env.battery_j,env.body_temperature_c,env.charger_termination_latched)
    def check_one(env,control_lock,lockstep,command,case,do_h6):
        global _D060_LAST_CASE_CONTEXT
        nonlocal step_total
        start=env.body.position; heading=env.body.heading; was_reset=env._step_count==0
        left=min(max(command[0],-m),m); right=min(max(command[1],-m),m)
        pfull,tfull=integrate_differential_drive(start,heading,left,right,track_width_m=D045_WHEEL_TRACK_WIDTH_METRES,wheel_radius_m=D045_WHEEL_RADIUS_METRES)
        _D060_LAST_CASE_CONTEXT={**case,"reset":case.get("reset"),"command":command,"p0":start,"p_full":pfull,"theta_full":tfull}
        oracle_gaps=tuple(oracle.workspace_gap(pfull,tfull,o) for o in oracle.ORACLE_LAYOUT)
        obstacle_violations=[i for i,g in enumerate(oracle_gaps) if g<0.]
        hx,hy=env._extent(tfull); room_bad=(pfull[0]<hx or pfull[0]>ROOM_SIDE_M-hx or pfull[1]<hy or pfull[1]>ROOM_SIDE_M-hy)
        if len(obstacle_violations)+int(room_bad)>1: raise AssertionError(f"H.4 multi-constraint oracle case={case} obstacle={obstacle_violations} room={room_bad}")
        if _h2b_requires_fresh_control(lockstep,obstacle_violations):
            fresh=D058Env(D058PhysicalConfig(ROOM_SIDE_M)); fresh.reset(options=explicit_current(env))
            fresh_result=fresh.step(command)
        else: fresh_result=None
        result=env.step(command); observation=result[0]; step_total+=1; counters["all_steps"]+=1
        assert env.last_transition.heading_after==tfull
        assert env.last_transition.actual_delta_left==left and env.last_transition.actual_delta_right==right
        assert env._previous_wheel_delta==(left,right)
        assert observation[6]==quantize_wheel_delta(left,env.config.encoder_quantum_rad)
        assert observation[7]==quantize_wheel_delta(right,env.config.encoder_quantum_rad)
        tr=env.last_transition; cfg=env.config._base
        effort=wheel_effort(left,right,m)
        assert tr.actuator_electrical_power_w==cfg.wheel_power_scale_w*effort
        assert tr.total_electrical_load_w==tr.electronics_electrical_power_w+tr.actuator_electrical_power_w
        assert tr.battery_after_j==min(cfg.battery_capacity_j,max(0.,tr.battery_before_j+tr.actual_stored_power_w*cfg.dt_seconds-tr.total_electrical_load_w*cfg.dt_seconds))
        for i,o in enumerate(oracle.ORACLE_LAYOUT):
            gap=oracle.workspace_gap(env.body.position,tfull,o)
            if gap < -TAU_C: raise AssertionError(f"H.4 endpoint obstacle violation case={case} obstacle={o[0]} gap={gap!r}")
        corner_violation=max(0.,hx-env.body.position[0],env.body.position[0]-(ROOM_SIDE_M-hx),hy-env.body.position[1],env.body.position[1]-(ROOM_SIDE_M-hy))
        if corner_violation>tau_room: raise AssertionError(f"H.4 room corner violation case={case} violation={corner_violation!r}")
        assert_reconstruction(env)
        if fresh_result is not None:
            compare_step(env,fresh,observation,fresh_result[0],ignore_index=True)
            counters["H2b_re_reset_steps"]+=1
        if lockstep and not obstacle_violations:
            control_result=control_lock.step(command)
            compare_step(env,control_lock,observation,control_result[0])
            counters["H2a_lockstep_steps"]+=1
        elif lockstep:
            counters["H2a_sequences_diverged"]+=1

        contact=env.last_obstacle_stage
        displacement=math.dist(start,env.body.position)
        if contact is not None:
            bound=wheel_delta_max+R_H+(0.05 if contact.primitive=="post" else next(o[3] for o in FROZEN_LAYOUT if o[0]==contact.obstacle_id))
        elif env.last_step_contact.resolved_by=="room":
            bound=wheel_delta_max+math.sqrt(2.)*B
        else:
            bound=wheel_delta_max
        if displacement>bound: raise AssertionError(f"H.4 step-kind displacement bound case={case} displacement={displacement!r} bound={bound!r}")
        for target in oracle.ORACLE_LAYOUT:
            if target[1] in ("arc","segment") and oracle.chord_crosses_centerline(start,env.body.position,target):
                raise AssertionError(f"H.4 no-crossing case={case} target={target[0]}")
        if contact is not None:
            i=next(i for i,o in enumerate(FROZEN_LAYOUT) if o[0]==contact.obstacle_id); ob=FROZEN_LAYOUT[i]
            case_key=(contact.obstacle_id,case["class"],case["sequence"],case["command_index"])
            contact_counts[case_key]+=1; class_counts[(contact.obstacle_id,case["class"])]+=1
            if contact.active_contact_count not in (1,2) or contact.active_contact_count!=len(contact.active_features):
                raise AssertionError(f"H.4 active feature telemetry mismatch case={case} contact={contact!r}")
            room=env.last_room_stage
            if (room.pushing_x_min or room.pushing_x_max or room.pushing_y_min or room.pushing_y_max
                    or room.removed_normal_displacement_m!=0. or room.slip_magnitude_m!=0.
                    or room.executed_endpoint!=pfull or room.unconstrained_endpoint!=pfull):
                raise AssertionError(f"H.4 obstacle step has nonzero room stage case={case} room={room!r}")
            if env.last_step_contact.resolved_by!="obstacle" or env.last_obstacle_stage is not contact:
                raise AssertionError(f"H.4 obstacle telemetry identity case={case}")
            if any(feature not in ("centre-line","inner-surface","outer-surface","end-cap") for _,feature in contact.active_features):
                raise AssertionError(f"H.4 non-normative feature label case={case} features={contact.active_features!r}")
            gaps=tuple(oracle.workspace_gap(env.body.position,tfull,item) for item in oracle.ORACLE_LAYOUT)
            if min(gaps)<-TAU_C: raise AssertionError(f"H.4 seven-obstacle legality case={case} gaps={gaps!r}")
            push=contact.push_out_magnitude_m
            universal=R_H+ob[3]
            if push>universal: raise AssertionError(f"H.4 universal push-out case={case} push={push!r} bound={universal!r}")
            if ob[1] in ("post","segment") and push>(B+(TAU_C if not was_reset else 0.)):
                raise AssertionError(f"H.4 convex push-out case={case} push={push!r} B={B!r}")
            if ob[1]=="arc": maxima["largest_arc_push_out_m"]=max(maxima.get("largest_arc_push_out_m",0.),push)
            margin=2*(A+ob[3])-2*TAU_C-displacement
            maxima["minimum_no_cross_margin_m"]=min(maxima.get("minimum_no_cross_margin_m",math.inf),margin)
            idem,idem_resid,idem_features,idem_n=_project(env.body.position,tfull,ob)
            idem_distance=math.dist(idem,env.body.position)
            if idem_distance>TAU_C: raise AssertionError(f"H.4 idempotence case={case} distance={idem_distance!r}")
            idempotence["exact"]+=int(idem==env.body.position); idempotence["within_tau_c"]+=1
            maxima["worst_accepted_candidate_residual_m"]=max(maxima.get("worst_accepted_candidate_residual_m",0.),contact.residual_m,idem_resid)
            if max(contact.residual_m,idem_resid)>TAU_C: raise AssertionError(f"H.8 residual case={case}")
            oracle_case={**case,"command":command,"p0":start,"p_full":pfull,"theta_full":tfull}
            best,no_free=_oracle_best_for_obstacle_step(env,tfull,ob,oracle,oracle_case)
            oracle_counts["obstacle_resolved_steps"]+=1; oracle_counts["rays_without_free_point"]+=no_free
            if push>best+TAU_C: raise AssertionError(f"O1 case={case} push={push!r} oracle={best!r}")
            excess=best-push
            maxima["oracle_excess_m"]=max(maxima.get("oracle_excess_m",0.),excess)
            if excess>oracle.EPSILON: raise AssertionError(f"O2 case={case} excess={excess!r} epsilon={oracle.EPSILON!r}")
            if case["class"]=="pocket" and contact.active_contact_count==2 and any(f=="inner-surface" for _,f in contact.active_features):
                pocket_two[(ob[0],case["pocket_sign"])]+=1
        else:
            if env.last_step_contact.resolved_by=="room": counters["room_steps"]+=1
            else: counters["free_steps"]+=1

        if do_h6:
            def independent_centerline_distance(point,o):
                if o[1]=="post": return math.dist(point,o[2])
                if o[1]=="segment": return oracle._point_seg(point,(o[2][0],o[2][1]),(o[2][2],o[2][3]))
                return oracle._point_arc_dist(point,o)
            nearby=[o for o in oracle.ORACLE_LAYOUT if independent_centerline_distance(start,o)<=R_H+o[3]+wheel_delta_max]
            penetrated_this_step=set()
            for k in range(1,64):
                sample,_=integrate_differential_drive(start,heading,left*k/64,right*k/64,track_width_m=D045_WHEEL_TRACK_WIDTH_METRES,wheel_radius_m=D045_WHEEL_RADIUS_METRES)
                for o in nearby:
                    penetration=max(0.,-oracle.workspace_gap(sample,heading+(tfull-heading)*k/64,o))
                    key=(o[0],case["class"])
                    if penetration>0.: penetrated_this_step.add(key)
                    if penetration>h6_max.get(key,0.): h6_max[key]=penetration; h6_case[key]={**case,"sample_k":k,"sample_count":64,"penetration_m":penetration}
                    if penetration>B: raise AssertionError(f"H.6 intermediate penetration case={case} obstacle={o[0]} k={k} penetration={penetration!r} B={B!r}")
            for key in penetrated_this_step: h6_nonzero[key]+=1
        return result

    # H.5 reset validation and all frozen reset-accept/reject starts.
    default=D060Env(); default.reset()
    assert default.body.position==(.75,.75) and default.body.heading==0. and default.station_center==(1.5,1.5)
    invalid_options=({"station_center":(1.4,1.5)},{"unknown":True},{"body_position":(.05,.05)},
        {"battery_j":D045_BATTERY_CAPACITY_J+1.},{"charger_termination_latched":1})
    for options in invalid_options:
        try: D060Env().reset(options=options)
        except ValueError: counters["H5_invalid_options"]+=1
        else: raise AssertionError(f"H.5 invalid reset accepted: {options!r}")
    for oi,k,u,cls in rays:
        ob=FROZEN_LAYOUT[oi]; radius=ob[3]+R_H+.005; p=(k[0]+radius*u[0],k[1]+radius*u[1])
        for theta in headings:
            D060Env().reset(options={"body_position":p,"heading":theta}); counters["ring_starts_accepted"]+=1
            for distance in (A+ob[3]-.001,0.):
                q=(k[0]+distance*u[0],k[1]+distance*u[1])
                try: D060Env().reset(options={"body_position":q,"heading":theta})
                except ValueError: counters["reset_rejections"]+=1
                else: raise AssertionError(f"H.5 penetrating reset accepted obstacle={ob[0]} class={cls} heading={theta!r} point={q!r}")

    # Ray and pocket sequences. Both environments reset separately for each sequence.
    for ri,(oi,k,u,cls) in enumerate(rays):
        ob=FROZEN_LAYOUT[oi]; radius=ob[3]+R_H+.005; p=(k[0]+radius*u[0],k[1]+radius*u[1])
        for hi,theta in enumerate(headings):
            for qname,commands in sequences:
                actual=D060Env(); control=D058Env(D058PhysicalConfig(ROOM_SIDE_M)); options=opts(p,theta)
                actual.reset(options=options); control.reset(options=options); lockstep=True
                for ci,command in enumerate(commands):
                    check_one(actual,control,lockstep,command,{"family":"ray","ray_index":ri,"obstacle":ob[0],"class":cls,"heading_index":hi,"sequence":qname,"command_index":ci,"reset":options},True)
                    if actual.last_obstacle_stage is not None: lockstep=False
    for oi,ob in enumerate(FROZEN_LAYOUT):
        if ob[1]!="arc": continue
        cx,cy,r0,a0,a1=ob[2]
        for j in range(9):
            alpha=a0+j*(a1-a0)/8
            for sign,heading,commands in (("+",alpha,((m,m),)*16+((m,-m),)*8+((-m,m),)*8),
                    ("-",alpha+math.pi,((-m,-m),)*16+((-m,m),)*8+((m,-m),)*8)):
                options=opts((cx,cy),heading); actual=D060Env(); control=D058Env(D058PhysicalConfig(ROOM_SIDE_M))
                actual.reset(options=options); control.reset(options=options); lockstep=True
                for ci,command in enumerate(commands):
                    check_one(actual,control,lockstep,command,{"family":"pocket","obstacle":ob[0],"class":"pocket","pocket_sign":sign,"heading_index":j,"sequence":"P"+sign,"command_index":ci,"reset":options},True)
                    if actual.last_obstacle_stage is not None: lockstep=False

    # Frozen pocket coverage is specifically two distinct inner-surface contacts per arc.
    for ob in FROZEN_LAYOUT:
        if ob[1]=="arc" and not any(pocket_two[(ob[0],sign)]>0 for sign in ("+","-")):
            raise AssertionError(f"pocket coverage missing two-contact concave case for {ob[0]}")

    # H.2(c): transplant the frozen D-058 wall/corner/grid probes at L=3.0.
    transplanted_rejected=[]
    starts=[]
    for kind,identifiers in (("wall",("x_min","x_max","y_min","y_max")),
                             ("corner",("x_min_y_min","x_max_y_min","x_min_y_max","x_max_y_max"))):
        for ident in identifiers:
            for variant in ("flush","near"):
                for hi,theta in enumerate(headings):
                    starts.append((f"{kind}:{ident}:{variant}",hi,d058_start(kind,ident,variant,theta,ROOM_SIDE_M),theta))
    for x in (.75,1.5,2.25):
        for y in (.75,1.5,2.25):
            for hi,theta in enumerate(headings): starts.append((f"grid:{x}:{y}",hi,(x,y),theta))
    for label,hi,p,theta in starts:
        gaps=tuple(oracle.workspace_gap(p,theta,o) for o in oracle.ORACLE_LAYOUT)
        oracle_penetrates=any(g<0. for g in gaps)
        try: D060Env().reset(options=opts(p,theta))
        except ValueError:
            if not oracle_penetrates: raise AssertionError(f"H.2(c) D060 rejected oracle-legal start label={label} heading={theta!r} gaps={gaps!r}")
            transplanted_rejected.append({"label":label,"heading_index":hi,"heading":theta,"position":p,"oracle_gaps_m":gaps})
            continue
        if oracle_penetrates: raise AssertionError(f"H.2(c) D060 accepted oracle-penetrating start label={label} heading={theta!r} gaps={gaps!r}")
        counters["H2c_accepted_starts"]+=1
        for ci,command in enumerate(u10):
            actual=D060Env(); control=D058Env(D058PhysicalConfig(ROOM_SIDE_M)); options=opts(p,theta)
            actual.reset(options=options); control.reset(options=options)
            pfull,tfull=integrate_differential_drive(p,theta,*command,track_width_m=D045_WHEEL_TRACK_WIDTH_METRES,wheel_radius_m=D045_WHEEL_RADIUS_METRES)
            if all(oracle.workspace_gap(pfull,tfull,o)>=0. for o in oracle.ORACLE_LAYOUT):
                ra=actual.step(command); rb=control.step(command); compare_step(actual,control,ra[0],rb[0]); counters["H2c_single_steps"]+=1
            seq_a=D060Env(); seq_b=D058Env(D058PhysicalConfig(ROOM_SIDE_M)); seq_a.reset(options=options); seq_b.reset(options=options)
            for si in range(64):
                cmd=u10[si%10]; state=seq_a.body.position; angle=seq_a.body.heading
                full,full_theta=integrate_differential_drive(state,angle,*cmd,track_width_m=D045_WHEEL_TRACK_WIDTH_METRES,wheel_radius_m=D045_WHEEL_RADIUS_METRES)
                if any(oracle.workspace_gap(full,full_theta,o)<0. for o in oracle.ORACLE_LAYOUT): break
                ra=seq_a.step(cmd); rb=seq_b.step(cmd); compare_step(seq_a,seq_b,ra[0],rb[0]); counters["H2c_lockstep_steps"]+=1

    # H.3 layout clearances from finite primitive geometry and closed-form bounds.
    def centerline_point_distance(point,obstacle):
        centre,_=_closest_centerline_point(point,obstacle)
        return math.dist(point,centre)
    def arc_pair_distance(first,second):
        def arc_point(o,angle):
            cx,cy,r0,_,_=o[2]; return cx+r0*math.cos(angle),cy+r0*math.sin(angle)
        candidates=[]
        for angle in (first[2][3],first[2][4]):
            p=arc_point(first,angle); q,_=_closest_centerline_point(p,second); candidates.append(math.dist(p,q))
        for angle in (second[2][3],second[2][4]):
            q=arc_point(second,angle); p,_=_closest_centerline_point(q,first); candidates.append(math.dist(p,q))
        c1=(first[2][0],first[2][1]); c2=(second[2][0],second[2][1]); axis=math.atan2(c2[1]-c1[1],c2[0]-c1[0])
        for o,other,angles in ((first,second,(axis,axis+math.pi)),(second,first,(axis,axis+math.pi))):
            for angle in angles:
                if _angle_on_sweep(angle,o[2][3],o[2][4]):
                    p=arc_point(o,angle); q,_=_closest_centerline_point(p,other); candidates.append(math.dist(p,q))
        if not candidates: raise AssertionError("H.3 arc pair distance has no finite candidates")
        return min(candidates)
    def centerline_distance(first,second):
        k1,k2=first[1],second[1]
        if k1=="post": return centerline_point_distance(first[2],second)
        if k2=="post": return centerline_point_distance(second[2],first)
        if k1=="segment" and k2=="segment":
            p,q=_segment_closest_pair((first[2][0],first[2][1]),(first[2][2],first[2][3]),(second[2][0],second[2][1]),(second[2][2],second[2][3])); return math.dist(p,q)
        if k1=="arc" and k2=="arc": return arc_pair_distance(first,second)
        if k1=="segment": segment,arc=first,second
        else: segment,arc=second,first
        p,q,_=_edge_contact_witness((segment[2][0],segment[2][1]),(segment[2][2],segment[2][3]),arc)
        return math.dist(p,q)
    wall_gaps=[]
    for ob in FROZEN_LAYOUT:
        _,kind,g,r=ob
        if kind=="post": xs=(g[0],); ys=(g[1],)
        elif kind=="segment": xs=(g[0],g[2]); ys=(g[1],g[3])
        else:
            cx,cy,r0,a0,a1=g; angles=[a0,a1]+[a for a in (0.,math.pi/2,math.pi,3*math.pi/2) if _angle_on_sweep(a,a0,a1)]
            xs=tuple(cx+r0*math.cos(a) for a in angles); ys=tuple(cy+r0*math.sin(a) for a in angles)
        wall_gaps.extend((min(xs)-r,ROOM_SIDE_M-max(xs)-r,min(ys)-r,ROOM_SIDE_M-max(ys)-r))
    minimum_wall_gap=min(wall_gaps)
    if minimum_wall_gap<=2*R_H: raise AssertionError(f"H.3 room-wall gap={minimum_wall_gap!r} <= hull diagonal {2*R_H!r}")
    pair_gaps={}
    for i,first in enumerate(FROZEN_LAYOUT):
        for second in FROZEN_LAYOUT[i+1:]:
            gap=centerline_distance(first,second)-first[3]-second[3]
            pair_gaps[f"{first[0]}-{second[0]}"]=gap
            if gap<=2*R_H: raise AssertionError(f"H.3 obstacle gap {first[0]}-{second[0]}={gap!r} <= hull diagonal {2*R_H!r}")
    dock_centre=(1.5,1.5)
    dock_gaps={o[0]:centerline_point_distance(dock_centre,o)-o[3] for o in FROZEN_LAYOUT}
    dock_clearance=min(dock_gaps.values())
    default_centre_gaps={o[0]:centerline_point_distance((.75,.75),o)-o[3] for o in FROZEN_LAYOUT}
    default_hull_gaps={o[0]:oracle.workspace_gap((.75,.75),0.,o) for o in oracle.ORACLE_LAYOUT}
    arc_openings={o[0]:2*o[2][2]*math.sin((o[2][4]-o[2][3])/2)-2*o[3] for o in FROZEN_LAYOUT if o[1]=="arc"}
    layout_metrics={"dock_clearance_by_obstacle_m":dock_gaps,"dock_clearance_m":dock_clearance,
        "minimum_room_wall_gap_m":minimum_wall_gap,"pairwise_obstacle_gaps_m":pair_gaps,
        "minimum_pairwise_obstacle_gap_m":min(pair_gaps.values()),"default_centre_clearance_by_obstacle_m":default_centre_gaps,
        "default_centre_clearance_m":min(default_centre_gaps.values()),"default_hull_clearance_by_obstacle_m":default_hull_gaps,
        "default_hull_clearance_m":min(default_hull_gaps.values()),"arc_opening_m":arc_openings,
        "inner_surface_radius_m":FROZEN_LAYOUT[0][2][2]-FROZEN_LAYOUT[0][3],"hull_diagonal_m":2*R_H}
    expected_display={"dock_clearance_m":"0.756","minimum_room_wall_gap_m":"0.375",
        "minimum_pairwise_obstacle_gap_m":"0.403","default_centre_clearance_m":"0.378",
        "default_hull_clearance_m":"0.241"}
    for key,display in expected_display.items():
        if format(layout_metrics[key],".3f")!=display: raise AssertionError(f"H.3 {key}={layout_metrics[key]!r} does not match displayed {display}")
    if format(arc_openings["A1"],".3f")!="0.643" or any(format(arc_openings[k],".3f")!="0.516" for k in ("A2","A3")):
        raise AssertionError(f"H.3 arc opening mismatch {arc_openings!r}")
    if format(layout_metrics["inner_surface_radius_m"],".3f")!="0.375" or format(2*R_H,".4f")!="0.2804":
        raise AssertionError("H.3 surface radius or hull diagonal mismatch")
    if not default._legal((.75,.75),0.): raise AssertionError("H.3 default pose illegal")

    return {"schema_version":"d060-v1","artifact_schema_version":ARTIFACT_SCHEMA_VERSION,
        "protocol_version":PROTOCOL_VERSION,"base_sha":BASE_SHA,"executed_commit_sha":executed_commit_sha,
        "coverage":{"feature_rays":len(rays),"headings":len(headings),"ray_steps":233472,"pocket_steps":1728,
            "steps_executed":step_total,"ring_starts_accepted":counters["ring_starts_accepted"],
            "reset_rejection_starts_rejected":counters["reset_rejections"],"oracle_rays_per_obstacle_step":oracle.PHI_COUNT},
        "checks":{"H.1_protected_byte_identity":"PASS","H.2_obstacle_free_identity":{"lockstep_steps":counters["H2a_lockstep_steps"],"re_reset_steps":counters["H2b_re_reset_steps"]},
            "H.3_layout_and_reset":{"status":"PASS",**layout_metrics},"H.4_contact_conformance":"PASS","H.5_reset":"PASS",
            "H.6_intermediate_penetration":{"maxima_m":{"|".join(k):v for k,v in sorted(h6_max.items())},"nonzero_step_counts":{"|".join(k):v for k,v in sorted(h6_nonzero.items())},"attaining_cases":{"|".join(k):v for k,v in sorted(h6_case.items())}},
            "H.7_determinism":"REGENERATION_REQUIRED","H.8_residual_max_m":maxima.get("worst_accepted_candidate_residual_m",0.),
            "O1":"PASS","O2":{"epsilon_m":oracle.EPSILON,"worst_excess_m":maxima.get("oracle_excess_m",0.),"rays_without_free_point":oracle_counts["rays_without_free_point"]},
            "pocket_two_contact_counts":{"|".join(k):v for k,v in sorted(pocket_two.items())}},
        "contact_counts":{"|".join(k):v for k,v in sorted(contact_counts.items())},
        "primitive_class_counts":{"|".join(k):v for k,v in sorted(class_counts.items())},
        "protected_sha256":protected_sha,"symbolic_penetration_bound_m":B,"room_corner_allowance_m":tau_room,
        "environment":{"python":sys.version,"numpy":np.__version__,"platform":platform.platform()}}


def write_d060_conformance(path:Path,executed_commit_sha:str|None=None)->Path:
    path.write_text(json.dumps(run_d060_conformance(executed_commit_sha),indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8"); return path


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--output",type=Path,required=True); parser.add_argument("--executed-commit-sha",required=True); args=parser.parse_args(); write_d060_conformance(args.output,args.executed_commit_sha)


if __name__=="__main__":main()
