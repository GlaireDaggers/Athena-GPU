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
- [ ] Implement table fog logic (look up fog density in table per pixel, blend output color w/ fog color)
- [ ] Work on tile dispatch logic (should be able to feed a table of command queues to tile dispatch, which in turn feeds commands to each tile core)
