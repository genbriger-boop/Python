

def parse_txt_file (file_path):

    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    all_lines = []

    for l in lines:
        strip_l = l.strip()
        if strip_l:
            all_lines.append(strip_l)
    
    return list(zip(all_lines[::2], all_lines[1::2]))
        

            
        