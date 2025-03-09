import sys
sys.path.append("../")
try:
	from bxbuild.tools import *
except:
	from build.tools import *
import re

args = sys.argv
modes = set()
if len(args) == 1:
    modes.add('--dep')
    modes.add('--unknown')
    modes.add('--notfound')
    modes.add('--nousage')
else:
    for _ in args[1:]:
        modes.add(_)

conf = get_config()

module_path = os.path.abspath(conf["module_path"])
component_path = ''
if "component_path" in conf:
    component_path = os.path.abspath(conf["component_path"])
version = get_module_version(module_path)

if isinstance(conf["lang_prefix"], str):
    lang_prefix = set(conf["lang_prefix"],)
else:
    lang_prefix = set(conf["lang_prefix"])

deprecated_uncheck = [
    os.path.join('install', 'unstep.php')
]
if "disabled_lang" in conf:
    disabled_lang = set(conf["disabled_lang"])
else:
    disabled_lang = set()

def walk_up_folder(path, depth=1):
    _cur_depth = 1        
    while _cur_depth < depth:
        path = os.path.dirname(path)
        _cur_depth += 1
    return path

def get_all_files(path, uncheck_dir=[], files = set()):
    for f_name in os.listdir(path):
        if not os.path.isdir(os.path.join(path, f_name)):
            pt = os.path.join(path, f_name)
            if '.php' == pt[-4:] and os.path.join('lang','ru') not in pt:
                files.add(os.path.join(path, f_name))
        else:
            uncheck = False
            for _ in uncheck_dir:
                if _ in os.path.join(path, f_name):
                    uncheck = True
            if not uncheck:
                files = get_all_files(os.path.join(path, f_name), uncheck_dir, files)
    return files

if version:
    all_files = get_all_files(module_path, [os.path.join('install','components')])
    if component_path:
        for dir_cmp_name in os.listdir(component_path):
            all_files = get_all_files(os.path.join(component_path, dir_cmp_name), [os.path.join(dir_cmp_name,'templates')], all_files)
            for dir_template_name in os.listdir(os.path.join(component_path, dir_cmp_name, 'templates')):
                all_files = get_all_files(os.path.join(component_path, dir_cmp_name, 'templates', dir_template_name), [], all_files)
    #print(all_files)
    #exit()
    for _ in all_files:
        file = _[len(module_path):]
        lang_file = os.path.join(module_path, 'lang', 'ru', file[1:])
        for level in range(1,5):
            if not os.path.exists(lang_file):
                c_lang_file = os.path.split(_)
                lang_file = os.path.join(walk_up_folder(os.path.dirname(_), level), 'lang', 'ru', c_lang_file[1])
        for level in range(1,5):
            if not os.path.exists(lang_file):
                c_lang_file = os.path.split(_)
                c_lang_file2 = os.path.split(walk_up_folder(_, 2))
                #print(c_lang_file2)
                lang_file = os.path.join(walk_up_folder(os.path.dirname(_), level), 'lang', 'ru', c_lang_file2[1], c_lang_file[1])
        lang_values = set()
        if os.path.exists(lang_file):
            with open(lang_file, 'r', encoding='utf-8') as fv:
                for line in fv:
                    result = re.findall(r'\$MESS\s?\[(?:"|\')([A-z0-9_]+)', line)
                    if len(result):
                        lang_values.add(*result)
        set_values = set()
        prepare_line = [" "]
        is_php = False
        is_comment = False
        with open(_, 'r', encoding='utf-8') as fv:
            cn_line = 0
            for line in fv:
                cn_line += 1

                #поиск русских букв
                if "--ru" in modes:
                    tag_php_start = re.findall(r'(<\?)', line.strip())
                    tag_php_end = re.findall(r'(\?>)', line.strip())
                    if len(tag_php_start) > len(tag_php_end):
                        is_php = True
                    elif len(tag_php_start) < len(tag_php_end):
                        is_php = False

                    #пропускаем или убиваем комментарии
                    if is_php:
                        line_prev = line
                        line = re.sub(r'^([\s\t]+#[^test]+)', '', line)
                        line = re.sub(r'^([\s\t]+//.*)', '', line)
                        line = re.sub(r'(//.*)$', '', line)
                        line = re.sub(r'(/\*.*\*/)$', '', line)
                        if not is_comment:
                            line = re.sub(r'^(/\*.*\*/)', '', line)
                            if len(re.findall(r'(/\*)', line.strip())):
                                is_comment = True
                        if is_comment and len(re.findall(r'(\*/)', line.strip())):
                            is_comment = False
                    if is_comment:
                        continue

                    #поиск русских буков
                    if len(re.findall(r'([А-я])', line.strip())):
                        print('ru? is deprecated?', line, 'in file', _, 'line', cn_line)

                dep_check = True
                for check_path in deprecated_uncheck:
                    if check_path in _:
                        dep_check = False
                if dep_check:
                    result_prev = re.findall(r'GetMessage\s?\($', prepare_line[-1].strip())
                    if len(result_prev):
                        result = re.findall(r'^(?:"|\'|)([A-z0-9_]+|)', line.strip())
                    else:
                        result = re.findall(r'GetMessage\s?\((?:\((?:"|\')|"|\'|)([A-z0-9_]+)(?:"|\'|\\\'|\\"|)', line.strip())
                    if len(result):
                        for ln in result:
                            if "--dep" in modes:
                                print('deprecated', ln, _)
                result_prev = re.findall(r'Loc::getMessage\s?\($', prepare_line[-1].strip())
                if len(result_prev):
                    result = re.findall(r'^(?:"|\'|)([A-z0-9_]+|)', line.strip())
                else:
                    result = re.findall(r'Loc::getMessage\s?\((?:\((?:"|\')|"|\'|)([A-z0-9_]+)(?:"|\'|\\\'|\\"|)', line.strip())
                if len(result):
                    for ln in result:
                        set_values.add(ln)
                        if not ln in disabled_lang:
                            check = False
                            for _lang in lang_prefix:
                                if _lang in ln:
                                    check = True
                            if (check == False) and ("--unknown" in modes):
                                print('unknown code', ln, 'in file', _, 'line', cn_line)
                            if ln in lang_values:
                                pass
                            else:
                                if "--notfound" in modes:
                                    print('not found', ln, 'in lang file', lang_file, 'line', cn_line)
                prepare_line = [line]
        no_usage = lang_values - set_values
        if len(no_usage) and "--nousage" in modes:
                for ln in no_usage:
                    print('unusage lang', ln, 'in lang file', lang_file)