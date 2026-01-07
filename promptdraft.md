Hi! I just finished all the assets for my game, and need help coding it using pygame (feel free to suggest something else if it's more suited). 
I'll start with basic requirements:
1. the game is a pixel art scrolling 2D platformer, with a 256x144 resolution. Nothing should EVER be off grid.
2. It's a tile based game, with each tile being 16x16 pixels, so the game world is 16 tiles wide and 9 tiles high.
3. The player is also 16x16 pixels, and can move left, right, jump, and fall due to gravity.
4. There are enemy characters also 16x16 pixels that move towards the player when in sight range.

Here's the Graphics pipeline, it's quite complicated:
First, construct a 3D 256x144x5 array, 5 values for each pixel: R,G,B, light, and Type. Here are the valid types:
1: floor: tiles that have player collision, except water
2: air: background tiles or the actual background image, lightbulbs.
3: water: water tiles
4: entity: player and enemy sprites, the player's sword
5: collectible: items that the player can pick up
6: hazard: spikes or other damaging tiles
7: particle: visual effects like dust or splashes, or the sword swipe
Next, render the game world into this array (more on this later), In the following order (so that the last appears on top). Initialize light at 0 except when noted otherwise:
1. Background image (light =255)
2. Background tiles
3. lightbulbs (light = 255)
4. tiles/spikes/water
5. collectibles
6. particles
7. enemies
8. player 
9. sword swipe (light = 255)
Okay, now the fancy part, that makes this raytraced:
for each pixel, loop over every pixel that has light=0, and calculate the "light" like this:
trace a line from the pixel to every lightbulb in range (128 pixel range). trace until you hit type 2, then trace until you either reach the bulb or hit type 4,1,or 6. if you hit the bulb first, increase light by 128-distance to bulb (make sure to cap to 255, so it won't overflow to 0 when three bulbs are relatively close to a pixel)
Next, draw the HUD/UI, text should be drawn using PixelifySans-VariableFont_wght.ttf. Make sure to set light to 255 for all of this.
Finally, draw this array to the screen, with the R,G,and B of each modified by this equation: final = original*(light/128+0.5). Upscale this grid USING NEAREST NEIGHBOR when drawing to the screen, so the final grid is HD while preserving a crisp pixel art style.

Now, for how to actualy do the rendering to the grid:
For tiles: IMPORTANT: each of the folders in the Assets folder has sprites that should be rendered differently. I'll go through them 1 by 1. 
## "Normal":
These are probably the simplest. Don't assume that they are just drawn straight to the buffer though, they're not. These textures are all black and white, and they all have a range from pure black to pure white. To use these, *linearly interpolate between two colors* using this value. for enemies, complete black is black, and complete white is red. this is done this way so that a single "normal" texture can be used for more than one tile type. for example, to make a wooden floor, you could take wood.png, and set the two colors to two similar shades of brown, and that's it. 
## Animationsheets
Easy. These are frames stacked horizontally, so the width and height are equal to the height, and the number of frames is width/height.
## Reflectionmaps
This is water, which is the most complicated. The idea is that this, during the rendering step, you don't render the pixel at the actual pixel's location, you user this to find the location you render at: first, go up the grid vertically until you find a type that isn't 3 or 1. Then, travel that distance minus 1 upward again.