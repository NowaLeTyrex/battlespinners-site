extends SceneTree
## Sonde d'enregistrement pour le dossier de presse, lancée par tools/capture/capture.py.
##
## Scénarios (--scenario=) :
##   - match : match de bots (mode spectateur) enregistré avec et sans HUD ; journalise
##     les moments à découper (lancements, frappes, capacités, éjections, explosions) ;
##   - customization : écran de personnalisation à 4 joueurs, changements de pièces
##     scriptés (CUSTOMIZATION_SCRIPT) ; un seul flux, l'écran étant de l'interface.
##
## Lancée avec --fixed-fps 60 : le temps de jeu avance d'1/60 s par tour de boucle,
## quel que soit le temps de capture. Tout le minutage se fait donc en tours de boucle
## (« tick »), jamais en millisecondes.
##
## Le projet s'ouvre en plein écran sur l'écran principal ; la sonde y reste et passe
## en fenêtre sans bordure de 1920×1080 dans son coin haut-gauche. Ne jamais passer
## --position ni --screen : sous Windows, Godot compte les coordonnées depuis l'écran
## le plus à gauche, pas depuis l'écran principal. L'écran principal doit faire au
## moins 1920×1080 physiques.
##
## Flux, écrits à chaque tour dans un ffmpeg chacun (données HDR linéaires en
## demi-flottants, converties en sRGB par ffmpeg, master RGB sans perte de matrice) :
##   - window : la fenêtre complète (HUD, annonces, filtres d'écran) ;
##   - world  : (match) un SubViewport 1920×1080 qui partage le World2D de la fenêtre
##     et recopie son cadrage, sans aucun CanvasLayer (même principe que PhotoMode).
## Une image vidéo n = le rendu du tick (record_start + n - 1) : décalage constant
## d'une image, la capture lisant le dernier rendu au début du tour.
##
## Les classes du jeu ne sont pas typées ici : une sonde --script compile avant que
## les autoloads existent (« Identifier not found »).
##
## Arguments utilisateur (après --) :
##   --events=<fichier.jsonl>  --out-window=<.mp4>  --out-world=<.mp4>  --ffmpeg=<exe>
##   --scenario=match|customization  --locale=en  --mute-music=1  --max-seconds=60
##   match : --arena=<res://….tres>  --bots=4  --difficulty=7  --rounds=1  --tail=1.5  --intro=0
##
## Emplacement : battlespinners-site/tools/capture/capture_probe.gd

const VERSUS_SCENE := "res://General/GameScene/versus_game.tscn"
const CUSTOMIZATION_SCENE := "res://General/CustomizationScene/customization_screen.tscn"
const DEFAULT_ARENA := "res://Environment/Arenas/ArenaData/arena-2OV.tres"
const PLAY_MODE_VERSUS := 1
const PLAY_MODE_DEMO := 3
const FPS := 60
const OUTPUT_SIZE := Vector2i(1920, 1080)

## Personnalisation : [tick depuis le début de l'enregistrement, panneau (0-3), action].
## « ready » = set_ready_state(true) ; jamais les 4, sinon le match démarre.
const CUSTOMIZATION_SCRIPT : Array = [
	[20, 0, "select_next_part"], [45, 1, "select_next_part"], [60, 2, "select_next_part_type"],
	[72, 0, "select_next_part"], [85, 3, "select_next_part"], [96, 2, "select_next_part"],
	[110, 1, "select_next_part"], [126, 0, "select_next_part_type"], [140, 3, "select_next_part"],
	[150, 0, "select_next_part"], [164, 2, "switch_ability_details_visibilty"],
	[180, 1, "pick_random_parts"], [198, 3, "select_next_part_type"], [212, 3, "select_next_part"],
	[226, 0, "ready"], [250, 2, "switch_ability_details_visibilty"], [262, 2, "ready"],
	[284, 1, "ready"],
]
## Durée enregistrée de la personnalisation, en ticks.
const CUSTOMIZATION_LENGTH := 330
## Délais depuis l'arrivée sur l'écran de personnalisation : 4 joueurs, pièces tirées
## au hasard (sinon les 4 partent du même loadout par défaut), puis enregistrement.
const ROSTER_DELAY := 60
const RANDOMIZE_DELAY := 100
const CUSTOMIZATION_RECORD_DELAY := 150

var _args : Dictionary = {}
var _scenario : String = "match"
var _frame : int = 0
var _events : FileAccess
var _hooked_scene : Node
var _rounds_ended : int = 0
var _quit_at : int = -1
var _max_frames : int = 0
var _world_view : SubViewport
## source ("window" | "world") → {"pipe": FileAccess, "pid": int, "frames": int, "report": String}
var _encoders : Dictionary = {}
var _recording : bool = false
var _record_from : int = 0
var _record_start : int = -1
var _roster_at : int = -1


func _initialize() -> void:
	for raw : String in OS.get_cmdline_user_args():
		if raw.begins_with("--") and raw.contains("="):
			var parts : PackedStringArray = raw.substr(2).split("=", true, 1)
			_args[parts[0]] = parts[1]
	var path : String = _args.get("events", "")
	if path.is_empty():
		push_error("capture_probe : --events=<fichier> manquant")
		quit(2)
		return
	_scenario = _args.get("scenario", "match")
	_events = FileAccess.open(path, FileAccess.WRITE)
	_max_frames = int(float(_args.get("max-seconds", "60")) * FPS)
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_BORDERLESS, true)
	_place_window()


## Écran principal, coin haut-gauche, 1920×1080. Réappliqué tant que la fenêtre n'a
## pas la bonne taille : la sortie du plein écran rétablit la taille par défaut après coup.
func _place_window() -> void:
	var primary : int = DisplayServer.get_primary_screen()
	DisplayServer.window_set_current_screen(primary)
	DisplayServer.window_set_size(OUTPUT_SIZE)
	DisplayServer.window_set_position(DisplayServer.screen_get_position(primary))


func _process(_delta : float) -> bool:
	_frame += 1
	if root.size != OUTPUT_SIZE and _frame < 30:
		_place_window()
	if not _recording and _hooked_scene != null and root.size == OUTPUT_SIZE and _frame >= _record_from:
		_recording = true
		_record_start = _frame
		_log("record_start", {})
	if _recording:
		_capture_frame()
	if _frame == 2:
		_prepare()
	elif _frame == 5:
		if _scenario == "customization":
			_start_customization()
		else:
			_create_world_view()
			_start_match()
	elif _frame > 5:
		if _scenario == "customization":
			_step_customization()
		else:
			_hook_match_if_new()
	if _world_view != null:
		_follow_camera()
	if (_quit_at > 0 and _frame >= _quit_at) or _frame >= _max_frames:
		_log("end" if _quit_at > 0 else "timeout", {})
		_finish()
	return false


func _prepare() -> void:
	TranslationServer.set_locale(_args.get("locale", "en"))
	if _args.get("mute-music", "1") == "1":
		AudioServer.set_bus_mute(AudioServer.get_bus_index(&"Music"), true)
	var screens : Array[String] = []
	for i : int in DisplayServer.get_screen_count():
		screens.append("%d:%s@%s" % [i, DisplayServer.screen_get_size(i), DisplayServer.screen_get_position(i)])
	_log("window", {"scenario": _scenario, "size": str(root.size),
			"position": str(DisplayServer.window_get_position()),
			"screen": DisplayServer.window_get_current_screen(),
			"primary": DisplayServer.get_primary_screen(), "screens": screens})


#region Match

func _start_match() -> void:
	var gp : Node = root.get_node("GameParameters")
	var arena : Resource = load(_args.get("arena", DEFAULT_ARENA))
	gp.set("PLAY_MODE", PLAY_MODE_DEMO)
	gp.set("USE_TEAMS", false)
	gp.set("BOT_SPINNERS_AMOUNT", int(_args.get("bots", "4")))
	gp.set("BOT_DIFFICULTY", int(_args.get("difficulty", "7")))
	gp.set("ACTIVE_ARENA", arena)
	gp.set("SELECTED_ARENA", arena)
	gp.set("is_new_game", _args.get("intro", "0") == "1")
	var cm : Node = root.get_node("ControllerManager")
	cm.call("set_active_limit", 0)
	cm.call("set_join_policy", 0)
	gp.call("build_slot_assignments")
	change_scene_to_file(VERSUS_SCENE)
	_log("scene_requested", {"arena": arena.resource_path})


## Chaque manche recharge la scène de match : on se raccroche au nouveau GameManager.
func _hook_match_if_new() -> void:
	var scene : Node = current_scene
	if scene == null or scene == _hooked_scene or not scene.has_node("GameManager"):
		return
	_hooked_scene = scene
	var gm : Node = scene.get_node("GameManager")
	gm.connect("game_started", _on_game_started)
	gm.connect("round_ended", _on_round_ended)
	_log("scene_ready", {})


func _on_game_started() -> void:
	_log("game_started", {})
	for spinner : Node in get_nodes_in_group("spinners"):
		var id : String = spinner.name
		spinner.connect("spinning_started", func() -> void: _log("launch", {"spinner": id}))
		spinner.connect("contact_dealt", func(_target : Node, contact_type : int) -> void:
			if contact_type == 2:   # Utils.ContactType.STRIKE
				_log("strike", {"spinner": id}))
		spinner.connect("explosion", func() -> void: _log("explosion", {"spinner": id}))
		spinner.connect("eliminated", _on_eliminated.bind(id))
		var abilities : Node = spinner.get("ability_manager")
		if abilities == null:
			continue
		for key : String in ["ability_a", "ability_b"]:
			var ability : Resource = abilities.get(key)
			if ability != null:
				# Capacités dupliquées par toupie : pas de resource_path, on nomme par le script.
				var ability_name : String = ability.get_script().resource_path.get_file().get_basename()
				ability.connect("activated", func() -> void:
					_log("ability", {"spinner": id, "ability": ability_name}))


func _on_eliminated(entity : Node, id : String) -> void:
	var tip : Node = entity.get("tip_position_area")
	var ring_out : bool = tip != null and not bool(tip.get("is_in_arena"))
	_log("ring_out" if ring_out else "eliminated", {"spinner": id})


func _on_round_ended() -> void:
	_rounds_ended += 1
	_log("round_ended", {"round": _rounds_ended})
	if _rounds_ended >= int(_args.get("rounds", "1")):
		_quit_at = _frame + int(float(_args.get("tail", "1.5")) * FPS)

#endregion


#region Personnalisation

func _start_customization() -> void:
	root.get_node("GameParameters").set("PLAY_MODE", PLAY_MODE_VERSUS)
	var cm : Node = root.get_node("ControllerManager")
	cm.call("set_active_limit", 4)
	cm.call("ensure_at_least", 1)
	change_scene_to_file(CUSTOMIZATION_SCENE)
	_log("scene_requested", {"scene": CUSTOMIZATION_SCENE})


func _step_customization() -> void:
	if _hooked_scene == null:
		var scene : Node = current_scene
		if scene != null and scene.get("player_customization_panels") != null:
			_hooked_scene = scene
			_roster_at = _frame + ROSTER_DELAY
			_record_from = _frame + CUSTOMIZATION_RECORD_DELAY
			_log("scene_ready", {})
		return
	if _frame == _roster_at:
		root.get_node("ControllerManager").call("debug_fill_roster")
		_log("roster_filled", {})
	if _frame == _roster_at - ROSTER_DELAY + RANDOMIZE_DELAY:
		for player : int in 4:
			_customization_action(player, "pick_random_parts")
	if _record_start < 0:
		return
	var t : int = _frame - _record_start
	for step : Array in CUSTOMIZATION_SCRIPT:
		if int(step[0]) == t:
			_customization_action(int(step[1]), String(step[2]))
	if t == CUSTOMIZATION_LENGTH:
		_quit_at = _frame


func _customization_action(player : int, action : String) -> void:
	var panels : Dictionary = _hooked_scene.get("player_customization_panels")
	if not panels.has(player):
		_log("missing_panel", {"player": player})
		return
	var panel : Node = panels[player]
	if action == "ready":
		panel.call("set_ready_state", true)
	else:
		panel.call(action)
	_log("action", {"player": player, "action": action})

#endregion


#region Capture

## Vue « monde » : même World2D et même World3D (donc même Environment : glow,
## contraste) que la fenêtre, sans les CanvasLayer.
func _create_world_view() -> void:
	_world_view = SubViewport.new()
	_world_view.size = OUTPUT_SIZE
	_world_view.world_2d = root.world_2d
	_world_view.use_hdr_2d = root.use_hdr_2d
	_world_view.canvas_item_default_texture_filter = root.canvas_item_default_texture_filter
	_world_view.snap_2d_transforms_to_pixel = root.snap_2d_transforms_to_pixel
	_world_view.snap_2d_vertices_to_pixel = root.snap_2d_vertices_to_pixel
	_world_view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(_world_view)


## La caméra du match écrit le canvas_transform de la fenêtre (coordonnées de la
## résolution de base) ; l'étirement canvas_items est dans get_final_transform().
## On recompose les deux, ramenés à la taille de sortie : même cadrage que la fenêtre.
func _follow_camera() -> void:
	var to_output : float = float(OUTPUT_SIZE.x) / float(root.size.x)
	_world_view.canvas_transform = Transform2D.IDENTITY.scaled(Vector2(to_output, to_output)) \
			* root.get_final_transform() * root.canvas_transform


func _capture_frame() -> void:
	_write_frame("window", root.get_texture().get_image())
	if _world_view != null:
		_write_frame("world", _world_view.get_texture().get_image())


func _write_frame(source : String, image : Image) -> void:
	if not _encoders.has(source):
		if not _open_encoder(source, image):
			return
	var encoder : Dictionary = _encoders[source]
	if image.get_size() != OUTPUT_SIZE:
		push_error("capture_probe : %s fait %s au lieu de %s" % [source, image.get_size(), OUTPUT_SIZE])
		return
	if not OS.is_process_running(int(encoder["pid"])):
		push_error("capture_probe : ffmpeg (%s) s'est arrêté, voir %s" % [source, encoder["report"]])
		_finish()
		return
	var pipe : FileAccess = encoder["pipe"]
	pipe.store_buffer(image.get_data())
	encoder["frames"] = int(encoder["frames"]) + 1


## Le format d'entrée de ffmpeg dépend de celui de l'image (HDR 2D = linéaire).
func _open_encoder(source : String, image : Image) -> bool:
	var pix_fmt : String = ""
	var linear : bool = true
	match image.get_format():
		Image.FORMAT_RGBH:
			pix_fmt = "rgbf16le"
		Image.FORMAT_RGBAH:
			pix_fmt = "rgbaf16le"
		Image.FORMAT_RGB8:
			pix_fmt = "rgb24"
			linear = false
		Image.FORMAT_RGBA8:
			pix_fmt = "rgba"
			linear = false
	if pix_fmt.is_empty():
		push_error("capture_probe : format d'image %d non géré (%s)" % [image.get_format(), source])
		return false
	var out : String = _args.get("out-" + source, "")
	# zscale reste en RGB (gbrp) : une sortie YUV lui demanderait une matrice qu'il n'a pas.
	var filters : String = "format=gbrp"
	if linear:
		filters = "zscale=transferin=linear:transfer=iec61966-2-1:primariesin=709:primaries=709,format=gbrp"
	var args : PackedStringArray = [
		"-hide_banner", "-loglevel", "error", "-nostats", "-y",
		"-f", "rawvideo", "-pix_fmt", pix_fmt,
		"-s", "%dx%d" % [OUTPUT_SIZE.x, OUTPUT_SIZE.y], "-framerate", str(FPS), "-i", "-",
		"-vf", filters, "-c:v", "libx264rgb", "-preset", "veryfast", "-crf", "4", out]
	# Les erreurs de ffmpeg vont dans un fichier : son stderr n'est jamais lu ici.
	var report : String = out.get_basename() + "_ffmpeg.log"
	OS.set_environment("FFREPORT", "file=%s:level=16" % report.replace("\\", "/").replace(":", "\\:"))
	var process : Dictionary = OS.execute_with_pipe(_args.get("ffmpeg", "ffmpeg"), args)
	if process.is_empty():
		push_error("capture_probe : impossible de lancer ffmpeg")
		return false
	_encoders[source] = {"pipe": process["stdio"], "pid": process["pid"], "frames": 0, "report": report}
	_log("encoder", {"source": source, "pix_fmt": pix_fmt, "out": out})
	return true


func _finish() -> void:
	if _events == null:
		return
	_recording = false
	for source : String in _encoders:
		var encoder : Dictionary = _encoders[source]
		var pipe : FileAccess = encoder["pipe"]
		pipe.close()
		_log("encoder_closed", {"source": source, "frames": encoder["frames"]})
	# Attendre la fin de l'encodage avant de quitter (sinon fichiers tronqués).
	for source : String in _encoders:
		var pid : int = _encoders[source]["pid"]
		var waited : int = 0
		while OS.is_process_running(pid) and waited < 120000:
			OS.delay_msec(100)
			waited += 100
	_events.close()
	_events = null
	quit()

#endregion


## `tick` = tour de boucle de la sonde ; l'image vidéo correspondante est
## tick - record_start + 1 (voir l'en-tête).
func _log(kind : String, data : Dictionary) -> void:
	if _events == null:   # évènements de démontage, après la fermeture du journal
		return
	data["event"] = kind
	data["tick"] = _frame
	_events.store_line(JSON.stringify(data))
	_events.flush()
