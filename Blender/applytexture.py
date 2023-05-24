import bpy, glob, os, json

def clean_dupes() -> None:
	for obj in bpy.data.objects:
		for slot in obj.material_slots:
			if slot.name[-3:].isnumeric():
				if bpy.data.materials.get(slot.name[:-4]) == None: continue
				real_material = bpy.data.materials[slot.name[:-4]]
				wrong_material = slot.material
				slot.material = real_material
				bpy.data.materials.remove(wrong_material)

def main() -> None:
	base_path = 'C:/FModel/Output/Exports/'

	clean_dupes()

	for obj in bpy.data.objects:
		print(f'Processing object: {obj.name}')
		if obj.type != 'MESH':
			print('Object not a mesh! Skipping...')
			continue

		base_json_path = None

		for path in glob.glob(base_path + 'TBL/Content/**/*.json', recursive=True):
			if os.path.basename(path) != obj.name + '.json': continue
			base_json_path = path
			break
		
		if base_json_path == None:
			print('Could not find JSON file! Skipping...')
			continue

		static_materials = None

		with open(base_json_path) as file:
			json_data = json.load(file)

			static_mesh_data = None

			for mesh_property in json_data:
				if mesh_property.get('Type', None) != 'StaticMesh': continue
				static_mesh_data = mesh_property
				break

			if static_mesh_data == None:
				print('Could not find static mesh data. Skipping...')
				break

			static_materials = static_mesh_data.get('Properties', {}).get('StaticMaterials', [])

		for static_material in static_materials:
			if static_material.get('ImportedMaterialSlotName', None) in ['default', None]: continue
			material_interface = static_material.get('MaterialInterface', {})
			material_name = material_interface.get('ObjectName', '').split('\'')[1]

			print(f'Resolving: {material_name}')

			material_path = None

			try:
				with open(base_path + material_interface.get('ObjectPath', '').replace('.0', '.json')) as file:
					json_data = json.load(file)
					
					material_path = json_data.get('Textures', {}).get('L0_Map_C_and_A', None)

					if material_path == None:
						for key, value in json_data.get('Textures', {}).items():
							texture_name = value.split('.')[1]
							if texture_name.startswith('T_') and (texture_name.endswith('_C') or texture_name.endswith('_BC')): material_path = value

				if material_path == None:
					print('Could not resolve material! Skipping...')
					continue
			except FileNotFoundError:
				print('Could not find material instance! Maybe it was not dumped? Skipping...')
				continue

			material_path = base_path + material_path.split('.')[0] + '.png'

			print(f'Resolved texture to: {material_path}')

			for material_slot in obj.material_slots:
				if material_name not in material_slot.name: continue

				material = material_slot.material
				bsdf = material.node_tree.nodes['Principled BSDF']
				if bsdf.inputs['Base Color'].is_linked: material.node_tree.nodes.remove(bsdf.inputs['Base Color'].links[0].from_node)
				
				texture = material.node_tree.nodes.new('ShaderNodeTexImage')
				texture.image = bpy.data.images.load(material_path)
				material.node_tree.links.new(bsdf.inputs['Base Color'], texture.outputs['Color'])

				print('Applied texture!')

if __name__ == '__main__': main()