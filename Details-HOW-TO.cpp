TO-DO: Window/Menus
		ControlBarScheme
		Intro Map

** Mapped Images: will be searched only within a "MappedImages" or "INI" folder

** Experience Points Window: layout is only in GeneralsExpPoint.wnd; images are, eg: 
	GeneralsPowerMenu_China
	Defined in: SCPurchasePowers512.INI
	Found at: Data\INI\MappedImages\TextureSize_512
	* These are loaded from Data/English/Art/Textures

	
----

Button Bevel/Emboss preset (Photoshop settings)
	Style: Inner Bevel; Technique: Smooth
	Depth: 80%
	Direction: UpdateSize: 10px; Soften: 0px;
	Angle: 127 deg; Use Global Light [x]
	Altitude: 37 deg; Rest = default

// SCHEME TO SVG

--- General Info

Commandbar texture size: 4096 x 1024
ImagePart rect size: 3840 x 714
Image entries defined in: \Data\INI\MappedImages\HandCreated\HandCreatedMappedImages.INI
	Eg: InGameUIGLABase

	@ ControlBarScheme.ini
	/*  ImagePart
		Position X:0 Y:1260
		Size X:3839 Y:900	
	*/
	@ HandCreatedMappedImages.INI
	/*	MappedImage InGameUIGLABase
			Texture = SUCommandBar.tga
			TextureWidth = 4096
			TextureHeight = 1024
			Coords = Left:0 Top:123 Right:3839 Bottom:1023	;;Notice that Size Y = Bottom - Top
			Status = NONE
		End	
	*/

--- Commandline commands:

# Generate SVG
python scheme_to_svg.py --generate --scheme GLA8x6 --scheme-file INI/ControlBarScheme.ini 

# Update Scheme from SVG
python scheme_to_svg.py --update --svg GLA8x6_scheme_NEW.svg --scheme GLA8x6 --scheme-file INI/ControlBarScheme.ini

	python scheme_to_svg.py --updatenew --svg GLA8x6_scheme.svg --scheme America8x6 --scheme-file INI/ControlBarScheme.ini	//outputs: ControlBarScheme_updated.ini
	

// WND to SVG

# Generate SVG from WND
python wnd_to_svg.py GenPowersShortcutBarUS.wnd --ini SAControlBar512.INI

python wnd_to_svg.py GeneralsExpPoints.wnd
	
	(Defaults to MappedImages and Art/Textures).
	
1182 x 1293

# Generate WND back from SVG
python wnd_to_svg.py <file.wnd> --update --svg <file.svg>	//-updatenew outputs a new file

	python wnd_to_svg.py GenPowersShortcutBarUS.wnd --update --svg GenPowersShortcutBarUS_NEW.svg

	python wnd_to_svg.py GeneralsExpPoints_NEW.wnd --update --svg GeneralsExpPoints_NEW.svg
	python wnd_to_svg.py GeneralsExpPoints_labeled.wnd --update --svg GeneralsExpPoints_NEW.svg	
	
	python wnd_to_svg.py ControlBar.wnd --updatenew --svg ControlBar_NEW.svg
	
----

** Updated Files:

	Data/INI/ControBarScheme.ini		// Fullscreen: Screensize and main button placement, *factions
	Window/ControlBar.wnd 				// Center-bottom: Controlbar item placement (*factions)
	Window/GenPowersShortcutBarUS.wnd 	// Center-Right: powers shortcut bar
	Window/GeneralsExpPoints.wnd 		// Center: Generals Points purchase panel 
	
  > Window/GenPowersShortcutBarChina.wnd
  > Window/GenPowersShortcutBarGLA.wnd
  > Window/GenPowersShortcutBarUS.wnd
  
  > Window\ReplayControl.wnd
  
  MapSelectMenu.wnd
  MultiplayerLoadScreen.wnd | Mp_Loaduserinterface_00b.tga
  GameInfoWindow.wnd
  LanLobbyMenu.wnd
  
  --
  
  > Window\ControlBarPopupDescription.wnd
  > Window\Diplomacy.wnd
  > Window\InGameChat.wnd
  > Window\DisconnectScreen.wnd
  > Window\MessageBox.wnd
  > Window\PopupBuddyListNotification.wnd
  > Window\QuitMessageBox.wnd
  > Window\QuitNoSave.wnd
	
  ! Window\Menu\SkirmishGameOptionsMenu.wnd
  ! Window\Menu\LanGameOptionsMenu.wnd
  
  window\menus\lanmapselectmenu.wnd
  window\menus\mapselectmenu.wnd
  window\menus\skirmishmapselectmenu.wnd
  
  
	
---

Data\INI\HandCreatedMappedImages.INI
	MappedImage MainMenuRuler {   Texture = MainMenuRuleruserinterface.tga }

---
** Boss ProUI commandbar texture:

Ref Screen Resolution (4k) = 3840 x 2160
1.2 width x 0.9 height

	** Gadget Parent Size (Black BG): 3434 x 1844 [@ 201 x 160]
		Opt: 3432 x 1844 [@ 206 x 160]
	   "Line" Width = 3410

Blue BG tweak: Hue -25, Saturation -12

3840 x 697 out of 4096 x 1024 (texture size)

