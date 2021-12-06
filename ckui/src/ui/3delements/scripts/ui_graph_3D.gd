extends Spatial

signal filtering_done

const MIN_ZOOM_3D = 20
const MAX_ZOOM_3D = 90
const TOUCH_ZOOM_SPEED = 0.1

var root_node : Object = null

# Left Mouse Button Drag vars
var mouse_lmb_is_pressed := false
var last_lmb_drag_pos := Vector2.ZERO
var new_lmb_drag_pos := Vector2.ZERO
var is_lmb_dragging_cam := false
var drag_lmb_sensitivity := 1.0
var drag_lmb_power := Vector2.ZERO

# Right Mouse Button Drag vars
var mouse_rmb_is_pressed := false
var last_rmb_drag_pos := Vector2.ZERO
var new_rmb_drag_pos := Vector2.ZERO
var is_rmb_dragging_cam := false
var drag_rmb_sensitivity := 1.0
var drag_rmb_power := Vector2.ZERO

var target_node : CloudNode = null
var cam_moving := false
var cam_target_zoom := 0.0
var selected_new_node := false
var original_zoom := 100.0
var is_active := true setget set_is_active
var loaded_data_filtered_ids := []

var api_response_data : Dictionary
var api_error := false

onready var graph = $GraphView
onready var graph_cam = $CameraArm/GraphCam3D
onready var graph_cam_arm = $CameraArm
onready var cam_tween = $CamMoveTween

export (Curve) var zoom_curve
export (NodePath) onready var main_ui = get_node(main_ui)

func _ready():
	_g.main_graph = graph
	graph.connect("order_done", self, "save_order")
	graph.connect("reset_camera", self, "reset_camera")
	_e.connect("graph_order", self, "main_graph_order")
	_e.connect("graph_randomize", self, "main_graph_rand")
	_e.connect("graph_spaceship", self, "update_spaceship_mode")
	_e.connect("go_to_graph_node_3d", self, "go_to_graph_node_3d")
	_e.connect("nodeinfo_hide", self, "hide_info")
	self.connect("filtering_done", self, "generate_graph")


func set_is_active(value:bool):
	is_active = value
	graph.is_active = value


func read_data( filter_by_kinds := [] ):
	var file = File.new()
	var new_data := {}
	loaded_data_filtered_ids.clear()
	
	if !_g.use_example_data and file.file_exists(_g.GRAPH_DUMP_JSON_PATH):
		file.open(_g.GRAPH_DUMP_JSON_PATH, file.READ)
		var file_len : float = float( file.get_len() )
		# warning-ignore:narrowing_conversion
		var update_mod : int = int( max( float( file.get_len() ) / 500000, 100.0 ) )
		var index := 0
		var benchmark_start = OS.get_ticks_usec()
		_g.msg( "Reading file ..." )
		_e.emit_signal("loading_start")
		_e.emit_signal("loading", 0, "Reading file" )
		yield(get_tree(), "idle_frame")
		
		while !file.eof_reached():
			var line = file.get_line()
			if line == "":
				index += 1
				continue
			
			var next_line = parse_json(line)
			new_data[index] = next_line
			index += 1
			
			if index % update_mod == 0: 
				_g.msg( "Reading file - line {0}".format([index]) )	
				_e.emit_signal("loading", (float( file.get_position() ) / file_len), "Reading file" )
				yield(get_tree(), "idle_frame")
		
		var benchmark_end = OS.get_ticks_usec()
		var benchmark_time = (benchmark_end - benchmark_start)/1000000.0
		
		_e.emit_signal("loading", 1, "Reading file" )
		_g.msg( "Reading file done! {0} Nodes in Graph | Loading time: {1}".format([index, stepify(benchmark_time, 0.01)]) )
		
		file.close()
	else:
		var example_data_file = load("res://scripts/tools/example_data.gd")
		var example_data = example_data_file.new()
		new_data = example_data.graph_data.duplicate()
		
	generate_graph(new_data)
	
	
func generate_graph(filtered_data_result:Dictionary):
	var file = File.new()
	var graph_node_positions := {}
	if file.file_exists(_g.GRAPH_NODE_JSON_PATH) and !_g.use_example_data:
		var new_graph_node_positions = Utils.load_json(_g.GRAPH_NODE_JSON_PATH)
		if typeof(new_graph_node_positions) == TYPE_DICTIONARY:
			graph_node_positions = new_graph_node_positions
	graph.create_graph_raw(filtered_data_result, filtered_data_result.size())
	yield(graph, "graph_created")
	graph.layout_graph(graph_node_positions)
	root_node = graph.root_node
	graph_cam_arm.translation = root_node.global_transform.origin
	cam_tween.interpolate_method(self, "change_cam_zoom", graph_cam.fov, 30, 0.5, Tween.TRANS_QUART, Tween.EASE_IN_OUT)
	cam_tween.start()
	
	_e.emit_signal("nodes_changed")
	graph.emit_signal("hide_nodes")


func get_graph_from_api( graph_id:String, query:String ):
	api_response_data.clear()
	api_error = false
	
	graph.start_streaming( graph_id )
	_g.api.connect("api_response", self, "api_response")
	_g.api.connect("api_response_total_elements", self, "api_response_total_elements")
	_g.api.connect("api_response_finished", self, "api_response_finished")
	
	var url : String = "/graph/" + graph_id + "/query/graph"
	_e.emit_signal("api_request", HTTPClient.METHOD_POST, url, query)


func api_response_total_elements( total_elements:int ):
	graph.total_elements = total_elements
	graph.stream_index_mod = max(int(float(total_elements) / 100), 1)


func api_response( chunk:String ):
	if chunk == "" or chunk == "[" or chunk == "\n]" or chunk == ",\n" or chunk.begins_with("Error:"):
		if chunk.begins_with("Error:"):
			api_error = true
		return
	
	var parse_result : JSONParseResult = JSON.parse( chunk.trim_prefix(",\n") )
	if parse_result.error == OK:
		_g.main_graph.add_streamed_object( parse_result.result )


func api_response_finished():
	_g.api.disconnect("api_response", self, "api_response")
	_g.api.disconnect("api_response_total_elements", self, "api_response_total_elements")
	_g.api.disconnect("api_response_finished", self, "api_response_finished")
	if api_error:
		print("API reported Error!")
		return
	_g.main_graph.end_streaming()
	print("API response finished!")


func main_graph_order():
	graph.graph_calc_layout()


func save_order(_saved_node_positions):
	var target_pos = graph.root_node.global_transform.origin
	var flytime = range_lerp( clamp(target_pos.distance_to(graph_cam_arm.global_transform.origin), 100, 1000), 100, 1000, 0.35, 1.5 )
	cam_tween.remove_all()
	cam_tween.interpolate_method(self, "change_cam_zoom", graph_cam.fov, 90, flytime, Tween.TRANS_QUART, Tween.EASE_IN_OUT)
	cam_tween.interpolate_property(graph_cam_arm, "global_transform:origin", graph_cam_arm.global_transform.origin, target_pos, flytime, Tween.TRANS_QUART, Tween.EASE_IN_OUT)
	cam_tween.start()
	# Node positions should be saved to file or local storage
#	Utils.save_json(_g.GRAPH_NODE_JSON_PATH, saved_node_positions)


func main_graph_rand():
	graph.graph_rand_layout()


func _physics_process(delta):
	if !is_active:
		return
	mouse_lmb_is_pressed = Input.is_action_pressed("left_mouse")
	var is_in_graph = true
	if mouse_lmb_is_pressed and !target_node and !selected_new_node and is_in_graph and !_g.spaceship_mode:
		new_lmb_drag_pos = get_viewport().get_mouse_position()
		if !is_lmb_dragging_cam:
			is_lmb_dragging_cam = true
			last_lmb_drag_pos = new_lmb_drag_pos
		else:
			drag_lmb_power = lerp(drag_lmb_power, (new_lmb_drag_pos - last_lmb_drag_pos), delta * 10 )
			last_lmb_drag_pos = new_lmb_drag_pos
	else:
		drag_lmb_power *= 54*delta
		is_lmb_dragging_cam = false
	
	mouse_rmb_is_pressed = Input.is_action_pressed("right_mouse")
	var is_rmb_in_graph = true
	if mouse_rmb_is_pressed and !target_node and !selected_new_node and is_in_graph and !_g.spaceship_mode:
		new_rmb_drag_pos = get_viewport().get_mouse_position()
		if !is_rmb_dragging_cam:
			is_rmb_dragging_cam = true
			last_rmb_drag_pos = new_rmb_drag_pos
		else:
			drag_rmb_power =  lerp(drag_rmb_power, (new_rmb_drag_pos - last_rmb_drag_pos), delta * 10 )
			last_rmb_drag_pos = new_rmb_drag_pos
	else:
		drag_rmb_power *= 54*delta
		is_rmb_dragging_cam = false
	
	
	var rot_drag_lmb_power = Vector3(drag_lmb_power.x, -drag_lmb_power.y, 0).rotated(Vector3.UP, graph_cam_arm.rotation.y)
	var rot_drag_rmb_power = Vector3(drag_rmb_power.x, -drag_rmb_power.y, 0).rotated(Vector3.UP, graph_cam_arm.rotation.y)
	graph_cam_arm.rotation_degrees.y -= drag_rmb_power.x*0.2
	graph_cam_arm.translation -= rot_drag_lmb_power + Vector3(0, rot_drag_rmb_power.y*0.5, 0)
	
	var new_zoom_level := 0.0
	if is_in_graph:
		if Input.is_action_just_released("zoom_in"):
			change_cam_zoom( max(graph_cam.fov * 0.95, MIN_ZOOM_3D) )
		elif Input.is_action_just_released("zoom_out"):
			change_cam_zoom( min(graph_cam.fov * 1.05, MAX_ZOOM_3D) )


func _input(event):
	if event is InputEventPanGesture:
		var zoom_value = clamp(graph_cam.zoom.x + (-event.delta.y * TOUCH_ZOOM_SPEED), MAX_ZOOM_3D, MIN_ZOOM_3D)
		change_cam_zoom(Vector2.ONE * zoom_value)


func zoom_out():
	original_zoom = graph_cam.fov
	cam_tween.remove_all()
	cam_tween.interpolate_method(self, "change_cam_zoom", graph_cam.fov, 40, 0.7, Tween.TRANS_EXPO, Tween.EASE_OUT)
	cam_tween.start()


func zoom_in():
	cam_tween.remove_all()
	cam_tween.interpolate_method(self, "change_cam_zoom", graph_cam.fov, original_zoom, 0.7, Tween.TRANS_EXPO, Tween.EASE_OUT)
	cam_tween.start()


func reset_camera():
	zoom_out()


func go_to_graph_node_3d(node_id, graph) -> void:
	if !is_active or graph != _g.main_graph:
		return
	if target_node != null:
		target_node.scene.is_selected = false
	
	target_node = _g.main_graph.graph_data.nodes[node_id]
	graph.emit_signal("hide_nodes")
	graph.emit_signal("show_node", node_id)
	
	selected_new_node = true
	$NewNodeSelectionTimer.start()
	var target_pos = target_node.scene.global_transform.origin
	var flytime = range_lerp( clamp(target_pos.distance_to(graph_cam_arm.global_transform.origin), 100, 1000), 100, 1000, 0.35, 1.5 )
	cam_tween.remove_all()
	cam_tween.interpolate_method(self, "change_cam_zoom", graph_cam.fov, 15, flytime, Tween.TRANS_QUART, Tween.EASE_IN_OUT)
	cam_tween.interpolate_property(graph_cam_arm, "global_transform:origin", graph_cam_arm.global_transform.origin, target_pos, flytime, Tween.TRANS_QUART, Tween.EASE_IN_OUT)
	cam_tween.start()
	target_node.scene.is_selected = true
	cam_moving = true


func _on_CamMoveTween_tween_all_completed() -> void:
	if target_node != null and cam_moving:
		cam_moving = false
		if !is_active:
			return
		_e.emit_signal("nodeinfo_show", target_node)


func _on_NewNodeSelectionTimer_timeout():
	selected_new_node = false


func hide_info():
	if target_node:
		target_node.scene.is_selected = false
	target_node = null
	cam_moving = false
	cam_tween.interpolate_method(self, "change_cam_zoom", graph_cam.fov, 30, 0.7, Tween.TRANS_EXPO, Tween.EASE_OUT)
	cam_tween.start()


func change_cam_zoom(zoom:float):
	graph_cam.fov = zoom
	var zoom_level = zoom_curve.interpolate( range_lerp(zoom, MIN_ZOOM_3D, MAX_ZOOM_3D, 0, 1) ) * 20
	_e.emit_signal("change_cam_zoom_3d", zoom_level)
