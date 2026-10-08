# Archived engineering probes for the RoboSim/Pymunk audit

- **status:** supporting research material; non-authorizing
- **date recorded:** 2026-10-08
- **Aweform executed source:** `e11ad91b3b7c649185bd1298ad5f3a791be571f8`
- **RoboSim executed source:** `86971d67a1eb0049653ebe842507a4ff30cb338d`

This archive supports the [audit](robosim-pymunk-physical-substrate-audit.md). It preserves the original local probe source and measurements rather than introducing a production adapter or repository test suite. It is not an official D/EXP protocol. Timing results are machine-dependent, and sampled trace equality is not universal bitwise determinism. The audit's focused test counts are separate from these probe scripts.

## Reproduction conditions

Use clean, separate checkouts at the exact source SHAs above and disposable virtual environments. No source edits are required. The original probes imported source using `PYTHONPATH`, rather than installing RoboSim as a package. RoboSim package metadata requires Pygame even though its physics/sensor core does not import it.

| Condition | Executed versions |
|---|---|
| RoboSim core/full-render proxy | Python 3.12.14, Pymunk 7.2.0, CFFI 2.1.1, Pygame 2.6.1 |
| RoboSim core only | Python 3.14.7, Pymunk 7.2.0, CFFI 2.0.0, no Pygame |
| Aweform component benchmark/focused tests | Python 3.14.7, NumPy 2.5.2, Gymnasium 1.3.0, Matplotlib 3.11.1, pytest 8.4.2 |

Platform: Linux x86_64, glibc 2.39, AMD EPYC 9V74 VM, nine visible virtual CPUs. Single process; no threaded solver. For the optional RoboSim render condition set `SDL_VIDEODRIVER=dummy`, `SDL_AUDIODRIVER=dummy`, and `PYGAME_HIDE_SUPPORT_PROMPT=1`, and pass `--render`. That invokes the real renderer without `tick()` and is an offscreen proxy, not a display-performance measurement.

The RoboSim probe's `random.seed(771)` belongs exclusively to its sensor RNG experiment. It did not execute an Aweform episode with that seed. The Aweform component probe uses explicit fixed actions and reset options, without seed-driven initialization, controller, or learner. These are component engineering measurements, not scientific lifetime comparisons.

The resized RoboSim observation in audit section 6 was a separate configuration-only check, not part of the archived main probe: body dimensions `(21.6,25.8)` px, wheel base `22.2` px, maximum speed `34.87167894882372` px/s, and six default 1/60 s microsteps. At `(1,1)` its displacement divided by 120 was `0.009685790259` m; at `(-1,+1)` its yaw was `0.104711246` rad. No RoboSim source or wheel model was changed. These rounded recorded values are not exact trace hashes.

## Original RoboSim probe source

Save this block outside either target source tree. Run with `PYTHONPATH` pointing to the pinned RoboSim checkout's `src`. It deliberately accesses private sensor bias for a reset diagnostic; it is not a recommended public API.

```python
"""Read-only audit probes of unchanged RoboSim; no Aweform integration."""
import hashlib
import json
import math
import os
import platform
import random
import statistics
import struct
import sys
import time
from dataclasses import replace

from robosim.config import SimulatorConfig, PhysicsConfig, StartConfig, NoiseConfig
from robosim.physics import PhysicsWorld
from robosim.robot import Robot
from robosim.sensors import EncoderPair, IMU, RangefinderArray
from robosim.types import DriveCommand, SensorPacket
import pymunk

CFG = SimulatorConfig()

def objects(config=CFG, noise=NoiseConfig()):
    w = PhysicsWorld(config)
    r = Robot(w)
    e = EncoderPair(config.physics, noise_cfg=noise)
    i = IMU(w.robot_body.angle, noise)
    f = RangefinderArray(config.physics.robot_size_px, noise, w.robot_shape)
    return w, r, e, i, f

def tick(obj, command, sensors=True):
    w, r, e, i, f = obj
    r.update(command)
    b = w.robot_body
    if sensors:
        dt = w.physics_cfg.timestep
        e.update(b.velocity, b.angle, b.angular_velocity, dt)
        i.update(b.angle, b.angular_velocity, dt)
        f.update(b, w.space, dt)

def state(obj):
    w, r, e, i, f = obj
    b = w.robot_body
    return (*b.position, b.angle, *b.velocity, b.angular_velocity,
            e.enc_left, e.enc_right, i.heading_deg, i.angular_vel_deg,
            f.range_front, f.range_right, f.range_back, f.range_left)

commands = [DriveCommand(1,1)]*650 + [DriveCommand(-.6,.8)]*450 + [DriveCommand(.8,.4)]*450 + [DriveCommand(-1,-1)]*450

def trace(noise=NoiseConfig(), interleave=False):
    random.seed(771)
    o = objects(noise=noise)
    h = hashlib.sha256()
    for c in commands:
        if interleave:
            random.gauss(0,1)
        tick(o,c)
        h.update(struct.pack('14d',*state(o)))
    return h.hexdigest()

def bench(kind,n):
    rates=[]
    for _ in range(3):
        o=objects()
        if kind=='render':
            from robosim.renderer import Renderer, Mode
            renderer=Renderer(CFG)
        start=time.perf_counter()
        for k in range(n):
            c=commands[k % len(commands)]
            tick(o,c,sensors=kind!='physics')
            if kind=='render':
                s=state(o)
                renderer.draw(o[1],SensorPacket(enc_left=s[6],enc_right=s[7],heading_deg=s[8],angular_vel_deg=s[9],range_front=s[10],range_right=s[11],range_back=s[12],range_left=s[13],timestamp=k/60),c,Mode.AUTO,k/60,rangefinders=o[4])
        rates.append(n/(time.perf_counter()-start))
    return {'steps_per_second':rates,'median':statistics.median(rates),'steps_per_trial':n,'trials':3}

def main():
    result={'runtime':sys.version,'platform':platform.platform(),'machine':platform.machine(),'pymunk':pymunk.version,'chipmunk':pymunk.chipmunk_version,'headless_pygame_imported':'pygame' in sys.modules}
    result['repeat_ideal']=[trace() for _ in range(5)]
    noise=NoiseConfig(.01,.001)
    result['repeat_noise']=[trace(noise) for _ in range(5)]
    result['noise_interleaved']=trace(noise,True)
    result['bench_physics']=bench('physics',30000)
    result['bench_sensors']=bench('sensors',30000)
    config_world=objects()[0]
    result['default_parameters']={'mass':config_world.robot_body.mass,'moment':config_world.robot_body.moment,'collision_slop':config_world.space.collision_slop,'iterations':config_world.space.iterations,'threaded':config_world.space.threaded}
    vectors={}
    for dt,n in [(1/60,6),(.1,1)]:
        cfg=replace(CFG,physics=replace(CFG.physics,timestep=dt))
        for name,c in [('forward',DriveCommand(1,1)),('reverse',DriveCommand(-1,-1)),('spin_positive',DriveCommand(-1,1)),('spin_negative',DriveCommand(1,-1)),('arc',DriveCommand(.5,1))]:
            o=objects(cfg)
            for _ in range(n):tick(o,c)
            vectors[f'{name}_dt_{dt}']=state(o)
    result['vectors']=vectors
    o=objects()
    for _ in range(2000):tick(o,DriveCommand(1,1))
    result['wall_push']=state(o)
    e=EncoderPair(CFG.physics,noise_cfg=NoiseConfig(0,.001))
    for _ in range(10):e.left.update(0,1/60)
    bias=e.left._noise.accumulated_bias
    e.reset()
    result['encoder_reset_bias']={'before':bias,'after':e.left._noise.accumulated_bias}
    # Copy physics while in loaded wall contact. Capture divergence; no organism experiments.
    w=o[0]; copyspace=w.space.copy(); copybody=next(iter(copyspace.bodies))
    divergences=[]
    for _ in range(20):
        w.space.step(1/60);copyspace.step(1/60)
        divergences.append(max(abs(a-b) for a,b in zip((*w.robot_body.position,*w.robot_body.velocity,w.robot_body.angle,w.robot_body.angular_velocity),(*copybody.position,*copybody.velocity,copybody.angle,copybody.angular_velocity))))
    result['loaded_contact_copy_max_difference']=max(divergences)
    result['resets_1000_seconds']=None
    start=time.perf_counter()
    for _ in range(1000):o=objects()
    result['resets_1000_seconds']=time.perf_counter()-start
    if '--render' in sys.argv:
        import pygame
        pygame.init()
        result['pygame']=pygame.version.ver
        result['render_driver']=pygame.display.get_driver()
        result['bench_render_dummy_uncapped']=bench('render',1000)
        pygame.quit()
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
```

## Original Aweform component benchmark source

Run with `PYTHONPATH` pointing to the pinned Aweform checkout's `src` in the declared Aweform runtime. This measures fixed-action environment transitions, not a learner/controller lifetime.

```python
"""Fixed-action component benchmark; no controller, learner, or seeded lifetime."""
import json, statistics, time, sys
from aweform.d045 import D045Env, D045_MAX_WHEEL_DELTA_RAD
from aweform.d058 import D058Env

commands=[(D045_MAX_WHEEL_DELTA_RAD,D045_MAX_WHEEL_DELTA_RAD),(-.4,.5),(.5,.2),(-.5,-.5)]
result={'python':sys.version}
for typ in [D045Env,D058Env]:
 rates=[]
 for _ in range(3):
  e=typ();e.reset(options={'battery_j':5328.0})
  start=time.perf_counter()
  for j in range(20000):
   obs,rew,term,trunc,info=e.step(commands[(j//150)%4])
   assert not term and not trunc and rew==0 and info=={}
  rates.append(20000/(time.perf_counter()-start))
 result[typ.__name__]={'steps_per_second':rates,'median':statistics.median(rates),'steps_per_trial':20000,'trials':3}
print(json.dumps(result,indent=2))
```

## Recorded outputs

### RoboSim Python 3.12 with dummy renderer

```json
{
  "runtime": "3.12.14 (main, Aug 25 2026, 14:00:49) [Clang 22.1.3 ]",
  "platform": "Linux-6.18.44-x86_64-with-glibc2.39",
  "machine": "x86_64",
  "pymunk": "7.2.0",
  "chipmunk": "2.0.1-ade7ed72849e60289eefb7a41e79ae6322fefaf3",
  "headless_pygame_imported": false,
  "repeat_ideal": [
    "f94865888687b32d73548bbcffbdfc6fb61cbae71fe78074ddb9525795e5cb6c",
    "f94865888687b32d73548bbcffbdfc6fb61cbae71fe78074ddb9525795e5cb6c",
    "f94865888687b32d73548bbcffbdfc6fb61cbae71fe78074ddb9525795e5cb6c",
    "f94865888687b32d73548bbcffbdfc6fb61cbae71fe78074ddb9525795e5cb6c",
    "f94865888687b32d73548bbcffbdfc6fb61cbae71fe78074ddb9525795e5cb6c"
  ],
  "repeat_noise": [
    "e050ad4a3704b1068bda3152be2cba9f5de35c20a247e0ad150a695dce22a047",
    "e050ad4a3704b1068bda3152be2cba9f5de35c20a247e0ad150a695dce22a047",
    "e050ad4a3704b1068bda3152be2cba9f5de35c20a247e0ad150a695dce22a047",
    "e050ad4a3704b1068bda3152be2cba9f5de35c20a247e0ad150a695dce22a047",
    "e050ad4a3704b1068bda3152be2cba9f5de35c20a247e0ad150a695dce22a047"
  ],
  "noise_interleaved": "0694de467a1a3b65ccdcd46141cf731b01c2a7067f1bb7370221ecb4032327dd",
  "bench_physics": {
    "steps_per_second": [
      85091.11920100308,
      97874.97603898811,
      100390.45764204866
    ],
    "median": 97874.97603898811,
    "steps_per_trial": 30000,
    "trials": 3
  },
  "bench_sensors": {
    "steps_per_second": [
      34730.94137681808,
      34803.364817153844,
      34644.02044328268
    ],
    "median": 34730.94137681808,
    "steps_per_trial": 30000,
    "trials": 3
  },
  "default_parameters": {
    "mass": 5.0,
    "moment": 2166.6666666666665,
    "collision_slop": 0.10000000149011612,
    "iterations": 10,
    "threaded": false
  },
  "vectors": {
    "forward_dt_0.016666666666666666": [
      330.66612496230425,
      324.0,
      0.0,
      131.8540102089823,
      0.0,
      0.0,
      758,
      758,
      0.0,
      0.0,
      200.0,
      200.0,
      200.0,
      200.0
    ],
    "reverse_dt_0.016666666666666666": [
      317.33387503769575,
      324.0,
      0.0,
      -131.8540102089823,
      0.0,
      0.0,
      -758,
      -758,
      0.0,
      0.0,
      200.0,
      200.0,
      200.0,
      200.0
    ],
    "spin_positive_dt_0.016666666666666666": [
      324.0,
      324.0,
      0.33330624811521514,
      0.0,
      0.0,
      6.592700510449113,
      -758,
      758,
      19.097041302342078,
      377.73391484247765,
      200.0,
      200.0,
      200.0,
      200.0
    ],
    "spin_negative_dt_0.016666666666666666": [
      324.0,
      324.0,
      -0.33330624811521514,
      0.0,
      0.0,
      -6.592700510449113,
      758,
      -758,
      -19.097041302342078,
      -377.73391484247765,
      200.0,
      200.0,
      200.0,
      200.0
    ],
    "arc_dt_0.016666666666666666": [
      328.994968472202,
      324.16056285935997,
      0.08332656202880379,
      98.69234794307884,
      5.78863250050434,
      1.6481751276122782,
      379,
      758,
      4.774260325585519,
      94.43347871061941,
      200.0,
      200.0,
      200.0,
      200.0
    ],
    "forward_dt_0.1": [
      324.0,
      324.0,
      0.0,
      200.0,
      0.0,
      0.0,
      1711,
      1711,
      0.0,
      0.0,
      200.0,
      200.0,
      200.0,
      200.0
    ],
    "reverse_dt_0.1": [
      324.0,
      324.0,
      0.0,
      -200.0,
      0.0,
      0.0,
      -1711,
      -1711,
      0.0,
      0.0,
      200.0,
      200.0,
      200.0,
      200.0
    ],
    "spin_positive_dt_0.1": [
      324.0,
      324.0,
      0.0,
      0.0,
      0.0,
      10.0,
      -1711,
      1711,
      0.0,
      572.9577951308232,
      200.0,
      200.0,
      200.0,
      200.0
    ],
    "spin_negative_dt_0.1": [
      324.0,
      324.0,
      0.0,
      0.0,
      0.0,
      -10.0,
      1711,
      -1711,
      0.0,
      -572.9577951308232,
      200.0,
      200.0,
      200.0,
      200.0
    ],
    "arc_dt_0.1": [
      324.0,
      324.0,
      0.0,
      150.0,
      0.0,
      2.5,
      855,
      1711,
      0.0,
      143.2394487827058,
      200.0,
      200.0,
      200.0,
      200.0
    ]
  },
  "wall_push": [
    613.1000000014906,
    323.9999858067716,
    2.5836467289724285e-15,
    0.0,
    -8.881784197001252e-16,
    0.0,
    24796,
    24798,
    1.4803205332290061e-13,
    0.0,
    5.0,
    200.0,
    200.0,
    200.0
  ],
  "encoder_reset_bias": {
    "before": 0.00035219491030817607,
    "after": 0.00035219491030817607
  },
  "loaded_contact_copy_max_difference": 3.2970533443696082e-18,
  "resets_1000_seconds": 0.057386680000035994,
  "pygame": "2.6.1",
  "render_driver": "dummy",
  "bench_render_dummy_uncapped": {
    "steps_per_second": [
      1070.4838923325153,
      1042.6086190259111,
      1025.5614904548413
    ],
    "median": 1042.6086190259111,
    "steps_per_trial": 1000,
    "trials": 3
  }
}
```

### RoboSim Python 3.14 without Pygame

```json
{
  "runtime": "3.14.7 (main, Sep 24 2026, 17:58:18) [Clang 22.1.3 ]",
  "platform": "Linux-6.18.44-x86_64-with-glibc2.39",
  "machine": "x86_64",
  "pymunk": "7.2.0",
  "chipmunk": "2.0.1-ade7ed72849e60289eefb7a41e79ae6322fefaf3",
  "headless_pygame_imported": false,
  "repeat_ideal": [
    "f94865888687b32d73548bbcffbdfc6fb61cbae71fe78074ddb9525795e5cb6c",
    "f94865888687b32d73548bbcffbdfc6fb61cbae71fe78074ddb9525795e5cb6c",
    "f94865888687b32d73548bbcffbdfc6fb61cbae71fe78074ddb9525795e5cb6c",
    "f94865888687b32d73548bbcffbdfc6fb61cbae71fe78074ddb9525795e5cb6c",
    "f94865888687b32d73548bbcffbdfc6fb61cbae71fe78074ddb9525795e5cb6c"
  ],
  "repeat_noise": [
    "e050ad4a3704b1068bda3152be2cba9f5de35c20a247e0ad150a695dce22a047",
    "e050ad4a3704b1068bda3152be2cba9f5de35c20a247e0ad150a695dce22a047",
    "e050ad4a3704b1068bda3152be2cba9f5de35c20a247e0ad150a695dce22a047",
    "e050ad4a3704b1068bda3152be2cba9f5de35c20a247e0ad150a695dce22a047",
    "e050ad4a3704b1068bda3152be2cba9f5de35c20a247e0ad150a695dce22a047"
  ],
  "noise_interleaved": "0694de467a1a3b65ccdcd46141cf731b01c2a7067f1bb7370221ecb4032327dd",
  "bench_physics": {
    "steps_per_second": [
      94708.2372268338,
      90002.0321558856,
      91714.44574026963
    ],
    "median": 91714.44574026963,
    "steps_per_trial": 30000,
    "trials": 3
  },
  "bench_sensors": {
    "steps_per_second": [
      34039.20280690786,
      33944.041785260844,
      35734.27525515905
    ],
    "median": 34039.20280690786,
    "steps_per_trial": 30000,
    "trials": 3
  },
  "default_parameters": {
    "mass": 5.0,
    "moment": 2166.6666666666665,
    "collision_slop": 0.10000000149011612,
    "iterations": 10,
    "threaded": false
  },
  "vectors": {
    "forward_dt_0.016666666666666666": [
      330.66612496230425,
      324.0,
      0.0,
      131.8540102089823,
      0.0,
      0.0,
      758,
      758,
      0.0,
      0.0,
      200.0,
      200.0,
      200.0,
      200.0
    ],
    "reverse_dt_0.016666666666666666": [
      317.33387503769575,
      324.0,
      0.0,
      -131.8540102089823,
      0.0,
      0.0,
      -758,
      -758,
      0.0,
      0.0,
      200.0,
      200.0,
      200.0,
      200.0
    ],
    "spin_positive_dt_0.016666666666666666": [
      324.0,
      324.0,
      0.33330624811521514,
      0.0,
      0.0,
      6.592700510449113,
      -758,
      758,
      19.097041302342078,
      377.73391484247765,
      200.0,
      200.0,
      200.0,
      200.0
    ],
    "spin_negative_dt_0.016666666666666666": [
      324.0,
      324.0,
      -0.33330624811521514,
      0.0,
      0.0,
      -6.592700510449113,
      758,
      -758,
      -19.097041302342078,
      -377.73391484247765,
      200.0,
      200.0,
      200.0,
      200.0
    ],
    "arc_dt_0.016666666666666666": [
      328.994968472202,
      324.16056285935997,
      0.08332656202880379,
      98.69234794307884,
      5.78863250050434,
      1.6481751276122782,
      379,
      758,
      4.774260325585519,
      94.43347871061941,
      200.0,
      200.0,
      200.0,
      200.0
    ],
    "forward_dt_0.1": [
      324.0,
      324.0,
      0.0,
      200.0,
      0.0,
      0.0,
      1711,
      1711,
      0.0,
      0.0,
      200.0,
      200.0,
      200.0,
      200.0
    ],
    "reverse_dt_0.1": [
      324.0,
      324.0,
      0.0,
      -200.0,
      0.0,
      0.0,
      -1711,
      -1711,
      0.0,
      0.0,
      200.0,
      200.0,
      200.0,
      200.0
    ],
    "spin_positive_dt_0.1": [
      324.0,
      324.0,
      0.0,
      0.0,
      0.0,
      10.0,
      -1711,
      1711,
      0.0,
      572.9577951308232,
      200.0,
      200.0,
      200.0,
      200.0
    ],
    "spin_negative_dt_0.1": [
      324.0,
      324.0,
      0.0,
      0.0,
      0.0,
      -10.0,
      1711,
      -1711,
      0.0,
      -572.9577951308232,
      200.0,
      200.0,
      200.0,
      200.0
    ],
    "arc_dt_0.1": [
      324.0,
      324.0,
      0.0,
      150.0,
      0.0,
      2.5,
      855,
      1711,
      0.0,
      143.2394487827058,
      200.0,
      200.0,
      200.0,
      200.0
    ]
  },
  "wall_push": [
    613.1000000014906,
    323.9999858067716,
    2.5836467289724285e-15,
    0.0,
    -8.881784197001252e-16,
    0.0,
    24796,
    24798,
    1.4803205332290061e-13,
    0.0,
    5.0,
    200.0,
    200.0,
    200.0
  ],
  "encoder_reset_bias": {
    "before": 0.00035219491030817607,
    "after": 0.00035219491030817607
  },
  "loaded_contact_copy_max_difference": 3.2970533443696082e-18,
  "resets_1000_seconds": 0.05706553099997791
}
```

### Aweform Python 3.14 component benchmark

```json
{
  "python": "3.14.7 (main, Sep 24 2026, 17:58:18) [Clang 22.1.3 ]",
  "D045Env": {
    "steps_per_second": [
      15161.281015021395,
      14997.022292483696,
      14800.232606079537
    ],
    "median": 14997.022292483696,
    "steps_per_trial": 20000,
    "trials": 3
  },
  "D058Env": {
    "steps_per_second": [
      38445.59972916289,
      40583.08428136981,
      42065.9714151578
    ],
    "median": 40583.08428136981,
    "steps_per_trial": 20000,
    "trials": 3
  }
}
```

## Focused Aweform test output

The original run selected `tests/test_d045.py`, `tests/test_d052.py`, and `tests/test_d058.py`. The historical base required by the protected-source test was fetched first. No tests were skipped.

```text
...............................................                          [100%]
47 passed in 28.95s
```

The audit separately reports RoboSim's full suite (104 passed on Python 3.12 with dummy SDL) and core suite (87 passed on Python 3.14 without Pygame). Their full terminal/coverage logs were not retained in this appendix. The counts are recorded observations, not a substitute for replay against pinned source.
