"""Independent workspace-geometry oracle for D-060 evaluator checks.

This module intentionally does not import ``d060``. Its gap is computed from
rectangle edges and the actual finite centre-line geometry, independently of
the simulator's candidate curves.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np

from .d045 import D045_MAX_WHEEL_DELTA_RAD

ORACLE_LAYOUT = (
    ("A1", "arc", (1.50,2.00,.40,math.radians(30),math.radians(150)),.025),
    ("A2", "arc", (2.75,1.50,.40,math.radians(135),math.radians(225)),.025),
    ("A3", "arc", (.40,2.60,.40,math.radians(270),math.radians(360)),.025),
    ("S1", "segment", (1.175,.55,1.825,.55),.025),
    ("S2", "segment", (.55,1.10,.55,1.75),.025),
    ("P1", "post", (2.35,.60),.05),
    ("P2", "post", (2.45,2.45),.05),
)
PHI_COUNT=3600
EPSILON=1.0e-4
TAU=1.0e-12


def _corners(p,theta):
    co,si=math.cos(theta),math.sin(theta)
    return tuple((p[0]+sx*.09*co-sy*.1075*si,p[1]+sx*.09*si+sy*.1075*co)
                 for sx,sy in ((-1.,-1.),(1.,-1.),(1.,1.),(-1.,1.)))

def _cross(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def _on_segment(a,b,p): return min(a[0],b[0])<=p[0]<=max(a[0],b[0]) and min(a[1],b[1])<=p[1]<=max(a[1],b[1])
def _segments_intersect(a,b,c,d):
    x1,x2,x3,x4=_cross(a,b,c),_cross(a,b,d),_cross(c,d,a),_cross(c,d,b)
    return ((x1*x2<0 and x3*x4<0) or
            (x1==0 and _on_segment(a,b,c)) or (x2==0 and _on_segment(a,b,d)) or
            (x3==0 and _on_segment(c,d,a)) or (x4==0 and _on_segment(c,d,b)))

def _inside(p,poly):
    vals=[_cross(poly[i],poly[(i+1)%len(poly)],p) for i in range(len(poly))]
    return all(v>=0 for v in vals) or all(v<=0 for v in vals)

def _point_seg(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]; den=dx*dx+dy*dy
    t=0. if den==0 else max(0.,min(1.,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den))
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)

def _angle(theta,a0,a1):
    theta=(theta-a0)%(2*math.pi)+a0
    return theta<=a1

def _point_arc_dist(p,o):
    _,_,(cx,cy,r,a0,a1),_=o; dx,dy=p[0]-cx,p[1]-cy; angle=math.atan2(dy,dx)
    if math.hypot(dx,dy)>0 and _angle(angle,a0,a1): return abs(math.hypot(dx,dy)-r)
    e0=(cx+r*math.cos(a0),cy+r*math.sin(a0)); e1=(cx+r*math.cos(a1),cy+r*math.sin(a1))
    return min(math.dist(p,e0),math.dist(p,e1))

def _edge_curve_distance(a,b,o):
    kind,g=o[1],o[2]
    if kind=="post": return _point_seg((g[0],g[1]),a,b)
    if kind=="segment":
        c,d=(g[0],g[1]),(g[2],g[3])
        if _segments_intersect(a,b,c,d): return 0.
        return min(_point_seg(a,c,d),_point_seg(b,c,d),_point_seg(c,a,b),_point_seg(d,a,b))
    cx,cy,r,a0,a1=g
    if _point_seg((cx,cy),a,b)<=r and _angle(math.atan2((a[1]+b[1])/2-cy,(a[0]+b[0])/2-cx),a0,a1): return 0.
    # Closest point from arc to a segment: endpoint distances plus radial foot.
    best=min(_point_arc_dist(a,o),_point_arc_dist(b,o))
    dx,dy=b[0]-a[0],b[1]-a[1]; den=dx*dx+dy*dy
    if den:
        t=max(0.,min(1.,((cx-a[0])*dx+(cy-a[1])*dy)/den)); q=(a[0]+t*dx,a[1]+t*dy)
        angle=math.atan2(q[1]-cy,q[0]-cx)
        if _angle(angle,a0,a1): best=min(best,abs(math.dist(q,(cx,cy))-r))
    return best

def workspace_gap(p,theta,o):
    """dist(rectangle,K)-r using corners/edges, not C.1 constraint curves."""
    corners=_corners(p,theta); kind,g=o[1],o[2]
    if kind=="post":
        k=(g[0],g[1]); d=0. if _inside(k,corners) else min(_point_seg(k,corners[i],corners[(i+1)%4]) for i in range(4))
    elif kind=="segment":
        s0,s1=(g[0],g[1]),(g[2],g[3]); d=0. if (_inside(s0,corners) or _inside(s1,corners)) else min(_edge_curve_distance(corners[i],corners[(i+1)%4],o) for i in range(4))
    else:
        d=min((_point_arc_dist(c,o) for c in corners),default=math.inf)
        d=min(d,*(_edge_curve_distance(corners[i],corners[(i+1)%4],o) for i in range(4)))
        cx,cy,rr,a0,a1=g
        for i in range(4):
            a,b=corners[i],corners[(i+1)%4]; dx,dy=b[0]-a[0],b[1]-a[1]; fx,fy=a[0]-cx,a[1]-cy
            aa=dx*dx+dy*dy; bb=2*(fx*dx+fy*dy); cc=fx*fx+fy*fy-rr*rr; disc=bb*bb-4*aa*cc
            if disc>=0:
                for t in ((-bb-math.sqrt(disc))/(2*aa),(-bb+math.sqrt(disc))/(2*aa)):
                    if 0<=t<=1 and _angle(math.atan2(a[1]+t*dy-cy,a[0]+t*dx-cx),a0,a1): d=0.
    return d-o[3]

def chord_crosses_centerline(p0,p1,o):
    """Independent exact finite chord/arc or chord/segment crossing check."""
    kind,g=o[1],o[2]
    if kind=="post": return False
    if kind=="segment": return _segments_intersect(p0,p1,(g[0],g[1]),(g[2],g[3]))
    cx,cy,r,a0,a1=g; dx,dy=p1[0]-p0[0],p1[1]-p0[1]; fx,fy=p0[0]-cx,p0[1]-cy
    aa=dx*dx+dy*dy
    if aa==0: return False
    bb=2*(fx*dx+fy*dy); cc=fx*fx+fy*fy-r*r; disc=bb*bb-4*aa*cc
    if disc<0: return False
    for t in ((-bb-math.sqrt(disc))/(2*aa),(-bb+math.sqrt(disc))/(2*aa)):
        if 0<=t<=1 and _angle(math.atan2(p0[1]+t*dy-cy,p0[0]+t*dx-cx),a0,a1): return True
    return False

def _ray_best(p,theta,o):
    rh=math.hypot(.09,.1075); bound=rh+o[3]+1e-9; best=math.inf; no_free=0
    for j in range(PHI_COUNT):
        ang=2*math.pi*j/PHI_COUNT; ux,uy=math.cos(ang),math.sin(ang); t=0.; found=False
        for _ in range(10000):
            gap=workspace_gap((p[0]+t*ux,p[1]+t*uy),theta,o)
            if gap>=0.: found=True; best=min(best,t); break
            t+=max(-gap,1e-13)
            if t>bound: break
        if not found:no_free+=1
    return best,no_free

def _feature_rays():
    """Return frozen (obstacle index, anchor, direction, class) order."""
    rays=[]
    for oi,o in enumerate(ORACLE_LAYOUT):
        _,kind,g,_=o
        if kind=="arc":
            cx,cy,r0,a0,a1=g
            for s in (1,2,3):
                angle=a0+s*(a1-a0)/4; k=(cx+r0*math.cos(angle),cy+r0*math.sin(angle)); n=(math.cos(angle),math.sin(angle))
                rays.extend(((oi,k,n,"arc-convex"),(oi,k,(-n[0],-n[1]),"arc-concave")))
            for angle,t in ((a0,(math.sin(a0),-math.cos(a0))),(a1,(-math.sin(a1),math.cos(a1)))):
                k=(cx+r0*math.cos(angle),cy+r0*math.sin(angle)); n=(math.cos(angle),math.sin(angle))
                rays.extend((oi,k,u,"arc-cap") for u in (t,((t[0]+n[0])/math.sqrt(2),(t[1]+n[1])/math.sqrt(2)),((t[0]-n[0])/math.sqrt(2),(t[1]-n[1])/math.sqrt(2))))
        elif kind=="segment":
            ax,ay,bx,by=g; dx,dy=bx-ax,by-ay; length=math.hypot(dx,dy); t=(dx/length,dy/length); n=(-t[1],t[0])
            for s in (.25,.5,.75):
                k=(ax+s*dx,ay+s*dy); rays.extend(((oi,k,n,"seg-face"),(oi,k,(-n[0],-n[1]),"seg-face")))
            for k,back in (((ax,ay),True),((bx,by),False)):
                base=(-t[0],-t[1]) if back else t
                rays.append((oi,k,base,"seg-cap"))
                rays.extend((oi,k,((base[0]+sign*n[0])/math.sqrt(2),(base[1]+sign*n[1])/math.sqrt(2)),"seg-cap") for sign in ((1.,-1.) if back else (1.,-1.)))
        else:
            k=g; rays.extend((oi,k,(math.cos(j*math.pi/4),math.sin(j*math.pi/4)),"post") for j in range(8))
    assert len(rays)==76
    return tuple(rays)

def oracle_best_free_distance(p,theta,obstacle):
    """Return (best distance, no-free ray count) for the frozen 3,600-ray scan."""
    return _ray_best(p,theta,obstacle)
