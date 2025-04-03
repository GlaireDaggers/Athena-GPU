# Athena-GPU
A simple tile based fixed function GPU written in MyHDL, intended to be *roughly* on par with GPUs c. 1999-2000  
This is a theoretical hardware implementation of the GPU for my fantasy console, the Nyxbox

**WORK IN PROGRESS - PROCEED AT YOUR OWN RISK**

# Current State

Executing `python3 test.py` rasterizes a triangle with rainbow vertex colors and a test crate texture into a 32x32 image and outputs the results to `test.png` (as well as outputting a depth buffer to `test_depth.png`).

# Goal

The current target is a simple tile based 3D GPU inspired by early PVR and 3DFX chipsets. The hardware is, effectively, *just* the rasterizer portion of the pipeline - the CPU is expected to perform transform, clipping, lighting, and tile binning. In fact, the CPU is even responsible for computing the "iterators" for each of a triangle's attributes (color, 1/w, s/w, t/w, and z/w), similar to the way 3DFX hardware was structured. This greatly simplifies the design of the rasterizer.

Theoretically: the CPU would generates a table of command queue pointers, one per onscreen tile, and submit this table to the tile dispatch. The tile dispatch would take care of dispatching the command queues to each physical tile core, as well as blitting each tile core's internal buffer back into a single "main" framebuffer in shared memory.

# To Do / Roadmap

- [X] Output interpolated Z/W coords to `test_depth.png` to verify depth is interpolated correctly
- [X] Test checkerboard pattern to verify S/T coords are interpolated correctly
- [X] Implement depth read, compare, & write logic
- [X] Implement texturing logic w/ support for multiple texture formats (w/ "texture cache" mechanism)
- [X] Combine interpolated vertex color w/ fetched texel color
- [X] Implement blending logic
- [X] Implement mip mapping support
- [X] Implement table fog logic (look up fog density in table per pixel, blend output color w/ fog color)
- [ ] Work on tile dispatch logic (should be able to feed a table of per-tile command queues to tile dispatch, which in turn feeds commands to each tile core)
- [ ] Logic for writing tile buffer contents into main "shared" memory (ideally: should be able to provide the address & dimensions of a framebuffer in main RAM & let the tile dispatch handle writing each tile's results into the correct location relative to given address)
- [ ] Start working on actually synthesizing to an evaluation board for testing (currently eyeing Arty Z7-20, but open to other suggestions)
- [ ] Implement video generator
