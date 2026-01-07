Hi! I just finished all the assets for my game, and need help coding it using pygame (feel free to suggest something else if it's more suited). 
I'll start with basic requirements:
1. the game is a pixel art scrolling 2D platformer, with a 256x144 resolution. Nothing should EVER be off grid.
2. It's a tile based game, with each tile being 16x16 pixels, so the game world is 16 tiles wide and 9 tiles high.
3. The player is also 16x16 pixels, and can move left, right, jump, and fall due to gravity.
4. There are enemy characters also 16x16 pixels that move towards the player when in sight range.

# Graphics
Here's the Graphics pipeline, it's quite complicated:
First, construct a 3D 256x144x5 array (list), 5 values for each pixel: R,G,B, light, and Type. Here are the valid types:
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
For tiles: IMPORTANT: each of the folders in the Assets folder has sprites that should be rendered differently. I'll go through them 1 by 1. With all of these, transparent pixels are *simply not rendered*.
### "Normal":
These are probably the simplest. Don't assume that they are just drawn straight to the buffer though, they're not. These textures are all black and white, and they all have a range from pure black to pure white. To use these, *linearly interpolate between two colors* using this value. for enemies, complete black is black, and complete white is red. this is done this way so that a single "normal" texture can be used for more than one tile type. for example, to make a wooden floor, you could take wood.png, and set the two colors to two similar shades of brown, and that's it. I'll refer to the color white corresponds to as "secondary" and the one black corresponds to as "primary" from now on.
### Animationsheets
Easy. These are frames stacked horizontally, so the width and height are equal to the height, and the number of frames is width/height. Once you've selected the right frame, treat like "normal".
### Reflectionmaps
This is water, which is the most complicated. The idea is that this, during the lighting step, you don't render the pixel at the actual pixel's location, you user this to find the location you render at: first, go up the grid vertically until you find a type that isn't 3 or 1. Then, travel that distance minus 1 upward again. for the horizontal, that is controlled by the grayscale value of the pixel, where you move over (value-0.5)\*vertical distance\*2 pixels, where vertical distance is the distance from the vertical position of the water pixel to the vertical position of the pixel it's reflecting, and value is the pixel's grayscale brightness from 0-1. this is why we render top to bottom, so by the time we render a water pixel, we've already lit the pixel it's reflecting, letting us copy the light value.
### Brightnessmaps:
This is similar to normal, but you only need one color on top of the texture data. You then, for every pixel, set the output color to color*(greyscalevalue*2), where greyscalevalue is the texture grayscale brightness between 0 and 1.
### Numsheet:
Ignore this. This was a number font spritesheet before I decided to use a ttf font.

## Non-technical details
Since there's no specific rendering done to differentiate background tiles from the foreground, the primary and secondary colors used for tiles here should both be dark-ish. The background is normal, and should have a primary of black with a secondary of white.

That's it for graphics!


# Gameplay
## Main Charachter:
The main charachter is a white two legged creature with a sword. It's textures are player_idle_spritesheet and player_walk_spritesheet. the walking spritesheet is facing right, so mirror it horizontally when the player is walking left. The sword is not part of this, and is instead in sword.png. Both of these should have the primary color be black and the secondary by white.
it should have wall jumps and slide, the sword should face toward the direction the player is moving, and they swing with E. when they swing, the animated swordswipe in swipe_spritesheet is played. Jumping on spikes should kill you.
## Enemies:
The enemies are slimes that chase the player, and he has to kill them with his sword. When they are killed, which takes two swipes (one swipe hits all enemies in range), they drop a lot of coins, and some super coins (both have assets), and spawn some particles (including normal particles and smoke particles, which have a primary of a random shade of grey, and are an animationsheet), with some screenshake. these coins duplicate and bounce up once when they hit the ground, it should be as satisfying as possible. They are always in idle animation, and have a primary of black and a secondary of pure red.

## Coins
have a primary of gold and a secondary of a light shade of gold

# Other requirements:
There has to be a level editor, where you can place any of the tiles in the normal folder with any primary and secondary colors you choose, either background or foreground layer, place lightbulbs, spikes, etc. You should also be able to eyedropper tool an existing tile you placed, or even one from another level. You should be able to save levels to a .level file in the "Outputs folder", and there should be a menu where you can choose what levels are in the actual game and in what order. Make this polished as well.