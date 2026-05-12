import ast
import os

def get_base_names(bases):
    names = []
    for base in bases:
        if isinstance(base, ast.Name):
            names.append(base.id)
        elif isinstance(base, ast.Attribute):
            names.append(base.attr)
    return ", ".join(names)

def parse_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    tree = ast.parse(content)
    classes = []
    
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_info = {
                'name': node.name,
                'bases': get_base_names(node.bases),
                'docstring': ast.get_docstring(node),
                'attributes': [],
                'field_validators': [],
                'model_validators': [],
                'domain_methods': [],
                'properties': []
            }
            
            for item in node.body:
                if isinstance(item, ast.AnnAssign):
                    attr_name = item.target.id
                    attr_type = ast.unparse(item.annotation) if hasattr(ast, 'unparse') else ""
                    # The previous generator seemed to struggle with some types, 
                    # but ast.unparse is clean. We will use ast.unparse.
                    # Wait, let's just make it clean
                    # Let's handle Optional or | None etc.
                    class_info['attributes'].append((attr_name, attr_type))
                elif isinstance(item, ast.FunctionDef):
                    method_name = item.name
                    if method_name.startswith('__') and method_name != '__init__':
                        continue
                        
                    is_field_validator = False
                    is_model_validator = False
                    is_property = False
                    
                    for dec in item.decorator_list:
                        dec_name = ""
                        if isinstance(dec, ast.Name):
                            dec_name = dec.id
                        elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                            dec_name = dec.func.id
                        elif isinstance(dec, ast.Attribute):
                            dec_name = dec.attr
                        elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                            dec_name = dec.func.attr
                        
                        if dec_name == 'field_validator':
                            is_field_validator = True
                        elif dec_name == 'model_validator':
                            is_model_validator = True
                        elif dec_name in ('property', 'computed_field'):
                            is_property = True
                            
                    if is_field_validator:
                        class_info['field_validators'].append(method_name)
                    elif is_model_validator:
                        class_info['model_validators'].append(method_name)
                    elif is_property:
                        class_info['properties'].append(method_name)
                    else:
                        class_info['domain_methods'].append(method_name)
                        
            classes.append(class_info)
            
    return classes

def generate_markdown(models_dir, output_file):
    md_lines = ["# Esquema del Dominio (Modelos)\n"]
    
    for filename in sorted(os.listdir(models_dir)):
        if not filename.endswith('.py') or filename == '__init__.py':
            continue
            
        filepath = os.path.join(models_dir, filename)
        classes = parse_file(filepath)
        
        if not classes:
            continue
            
        md_lines.append(f"## Modulo: `{filename}`\n")
        
        for cls in classes:
            md_lines.append(f"### {cls['name']}")
            if cls['bases']:
                md_lines.append(f"**Herencia**: {cls['bases']}\n")
            else:
                md_lines.append("")
                
            if cls['docstring']:
                md_lines.append(f"{cls['docstring']}\n")
                
            if cls['attributes']:
                md_lines.append("**Atributos:**")
                for attr, atype in cls['attributes']:
                    if atype:
                        md_lines.append(f"- `{attr}`: {atype}")
                    else:
                        md_lines.append(f"- `{attr}`:")
                md_lines.append("")
                
            if cls['field_validators']:
                md_lines.append("**Field Validators:**")
                for m in cls['field_validators']:
                    md_lines.append(f"- `{m}()`")
                md_lines.append("")
                
            if cls['model_validators']:
                md_lines.append("**Model Validators:**")
                for m in cls['model_validators']:
                    md_lines.append(f"- `{m}()`")
                md_lines.append("")
                
            if cls['properties']:
                md_lines.append("**Propiedades:**")
                for m in cls['properties']:
                    md_lines.append(f"- `{m}`")
                md_lines.append("")
                
            if cls['domain_methods']:
                md_lines.append("**Métodos de Dominio:**")
                for m in cls['domain_methods']:
                    md_lines.append(f"- `{m}()`")
                md_lines.append("")
                
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines))

if __name__ == '__main__':
    models_dir = r'c:\Users\579j\Documents\DOCUMENTOS_B\Proyecto_Control_Asitencia\app_v2\zeci_manager_v2\src\domain\models'
    output_file = r'c:\Users\579j\Documents\DOCUMENTOS_B\Proyecto_Control_Asitencia\app_v2\zeci_manager_v2\docs\schema.md'
    generate_markdown(models_dir, output_file)
    print("schema.md generated successfully.")
