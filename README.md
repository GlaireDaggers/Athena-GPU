# Athena-GPU
A simple tile based fixed function GPU written in MyHDL, intended to be *roughly* on par with GPUs c. 1999-2000  
This is a theoretical hardware implementation of the GPU for my fantasy console, the Nyxbox

**WORK IN PROGRESS - PROCEED AT YOUR OWN RISK**

# Current State

Executing `python3 test.py` rasterizes a rainbow triangle into a 32x32 image and outputs the results to `test.png`.

# To Do / Roadmap

- [ ] Output interpolated Z/W coords to `test_depth.png` to verify depth is interpolated correctly
- [ ] Test checkerboard pattern to verify S/T coords are interpolated correctly
- [ ] Implement depth read, compare, & write logic
- [ ] Implement basic texture fetch logic (w/ "texture cache" mechanism)
- [ ] Combine interpolated vertex color w/ fetched texel color
- [ ] Implement blending logic
- [ ] Stencil read/compare/write logic?
- [ ] Implement table fog logic (look up fog density in table per pixel, blend output color w/ fog color)
- [ ] Work on tile dispatch logic (should be able to feed a table of per-tile command queues to tile dispatch, which in turn feeds commands to each tile core)
- [ ] Logic for writing tile buffer contents into main "shared" memory (ideally: should be able to provide the address & dimensions of a framebuffer in main RAM & let the tile dispatch handle writing each tile's results into the correct location relative to given address)
- [ ] Start working on actually synthesizing to an evaluation board for testing (currently eyeing Arty Z7-20, but open to other suggestions)
