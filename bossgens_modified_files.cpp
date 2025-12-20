Boss Generals Remastered - modified files

*HD	1280x720
FHD 1920 x 1080
QHD 2560 x 1440 [2732x683]
4k  3840 x 2160

Source: TexturesZH.big
	* [+] Art / Textures: sacommandbar.tga (4096x1024)
		Source resolution for sacommandbar: 1024x256
		Remaster resolution for sacommandbar: 4096x1024
		//sacommandbar_new.tga
		
		Positioning:
			ScreenCreationRes (4k) = 3840 x 2160
			vs
			ImagePart | Position, Size z
			
			VOffset = 327

	
	* [+] Art\Textures\sacontrolbar512_001.tga
	
	[[ found at 'Data\Ini\MappedImages\TextureSize_512\SAControlBar512.INI' ]]

	
	Art/Textures/sccpointer.dds

Source: \Data\INI\INIZH.big
	Data\Ini\ControlBarScheme.ini
	Data\Ini\MappedImages\HandCreated\HandCreatedMappedImages.ini
		//MappedImage InGameUIAmericaBase

	
==============
	; Gen Cameo Mapper v3 Auto-Generated INI File
	; Visit GenDev at http://gendev.gamemod.net/
	 
	MappedImage Topleft_Button
	Texture = sacontrolbar512_001.tga
	TextureWidth = 2048
	TextureHeight = 2048
	Coords = Left:400 Top:446 Right:720 Bottom:566
	Status = NONE
	End	
	
==============	

TO-DO next: 
	* Converting 'to' SVG should use the 'ScreenCreationRes' attribute as the SVG canvas size (X:800 Y:600 in the supplied file) and create the SVG rectangles (button elements) offset from the ImagePart/Position attribute (X and/or Y, it's X:0 Y:408 in the supplied file)
		//ImagePart
		//	Position X:0 Y:408
		//	Size X:800 Y:191

	
	* Converting back 'from' SVG should respect the canvas size of the SVG, and update that in ScreenCreationRes 
		Eg: ScreenCreationRes X:1920 Y:1080 // for an SVG canvas size of 1920x1080
	
*Other files of relevance, from INIZH.big:

//Command buttons setup:
CommandSet.ini | Eg: Command_AttackMove
					 Command_ConstructAmericaPowerPlant
			
//In-game Cursors			
InGameUI.ini