# Generate SVG
python overlay_generator.py --generate

# Update Scheme from SVG
python overlay_generator.py --update --svg output_overlay_with_images.svg --scheme ControlBarSchemeUSA.txt

# Generate SVG from WND
python wnd_to_svg.py GenPowersShortcutBarUS.wnd --ini SAControlBar512.INI

python wnd_to_svg.py GeneralsExpPoints.wnd
	
	(should default to MappedImages and Art/Textures).
	
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

