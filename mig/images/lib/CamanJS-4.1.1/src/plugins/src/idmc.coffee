###
IDMC plugins
###

# resetOriginalPixelData is broken, this is the way it should be

Caman.Filter.register "idmc_reset_original_pixeldata", () ->
  	@processPlugin "idmc_reset_original_pixeldata", null

Caman.Plugin.register "idmc_reset_original_pixeldata", () ->
	
	Log.debug "idmc_reset_original_pixeldata"

	@originalPixelData = Util.dataArray(@pixelData.length)
	@originalPixelData[i] = pixel for pixel, i in @pixelData
	@

# Adjust minimum and maximim pixel values

Caman.Filter.register "idmc_set_min_max_pixel_values", (min_pixel_value, max_pixel_value) ->
  @processPlugin "idmc_set_min_max_pixel_values", [min_pixel_value, max_pixel_value]


Caman.Plugin.register "idmc_set_min_max_pixel_values", (min_pixel_value, max_pixel_value) ->
	org_pixels = @originalPixelData	
	pixels = @pixelData
	width = @dimensions.width
	height = @dimensions.height

	if not @idmc_set_min_max_pixel_values_r_colormap?	
		@idmc_set_min_max_pixel_values_r_colormap = (i for i in [0...256])

	if not @idmc_set_min_max_pixel_values_g_colormap?	
		@idmc_set_min_max_pixel_values_g_colormap = (i for i in [0...256])

	if not @idmc_set_min_max_pixel_values_b_colormap?	
		@idmc_set_min_max_pixel_values_b_colormap = (i for i in [0...256])

	r_colormap = @idmc_set_min_max_pixel_values_r_colormap
	g_colormap = @idmc_set_min_max_pixel_values_g_colormap
	b_colormap = @idmc_set_min_max_pixel_values_b_colormap


	idx = (x,y) => (y*width + x) * 4

	for i in [0...256]
		#Log.debug "i: " +i+ ", " +min_pixel_value+ ", " + "max_pixel_value"


		index = Math.round((256 * (i - min_pixel_value)) / (max_pixel_value - min_pixel_value));
		#Log.debug "index1: " +index

		index = if index < 0
			0
		else if i > 255
			255
		else 
			index

		#Log.debug "index2: " +index		

		r_colormap[i] = if i < min_pixel_value
			0
		else if i > max_pixel_value
			255
		else
			index

		g_colormap[i] = if i < min_pixel_value
			0
		else if i > max_pixel_value
			255
		else
			index

		b_colormap[i] = if i < min_pixel_value
			0
		else if i > max_pixel_value
			255
		else 
			index


	for y in [0...height]
		for x in [0...width]
			#Log.debug "org_pixels[" +x+ "," +y+ "]: " + org_pixels[idx(x,y)]

			r = org_pixels[idx(x,y)]
			g = org_pixels[idx(x,y) + 1]
			b = org_pixels[idx(x,y) + 2]
			a = org_pixels[idx(x,y) + 3]
	
			pixels[idx(x,y)]     = r_colormap[r]
			pixels[idx(x,y) + 1] = g_colormap[g]
			pixels[idx(x,y) + 2] = b_colormap[b]
			pixels[idx(x,y) + 3] = 255	

	@

Caman.Filter.register "idmc_test", () ->
  	@processPlugin "idmc_test", []

Caman.Plugin.register "idmc_test", () ->
	@process "idmc_test", (rgba) ->
		Log.debug "IDMC test func"
		rgba
@