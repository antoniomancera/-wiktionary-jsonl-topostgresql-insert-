import json
import csv
import os
import re

from word import Word, WordDeclensionIrregular, WordSense

fr_extract = "C:/Users/Usuario/Desktop/apprendreCOsas/fr-extract.jsonl"
es_extract = "C:/Users/Usuario/Desktop/apprendreCOsas/es-extract.jsonl"
output_file_csv = "wiktionary_fr.csv"
output_file_txt = "wiktionary_fr.txt"
# prueba ="prueba.txt"
# prueba_tags ="prueba_tags.txt"
# prueba_pos ="prueba_pos.txt"
sound_csv = "sound_csv.csv"
last_word_id=50
last_word_sense_id=208
last_word_declension_non_exist_id=0
last_word_declension_irregular_id=0



def normalize_ipa(s: str) -> str:
    """Normaliza una cadena IPA para comparación:
       - trim, quitar delimitadores externos (/ [ \\ ] ( ) < > ' ")
       - colapsar espacios múltiples
       - devolver cadena limpia ('' si None/empty)
    """
    if not s:
        return ""
    # normalizar NBSP
    s = s.replace("\u00A0", " ").strip()
    # quitar delimitadores externos repetidos: \\ / [ ] ( ) < > " '
    s = re.sub(r'^[\\/\[\(\<\"\']+', '', s)
    s = re.sub(r'[\\/\]\)\>\'"]+$', '', s)
    s = s.strip()
    s = re.sub(r'\s+', ' ', s)
    return s



def obtener_id_por_ipa(ipa, archivo_csv,output_file):
    """
    Obtiene el ID de un sonido IPA. Si no existe, lo agrega al CSV y devuelve el nuevo ID.
    """
    ids_existentes = []
    ipa_encontrado = None

    # Verificar si el archivo existe y leerlo
    if os.path.exists(archivo_csv):
        try:
            with open(archivo_csv, 'r', newline='', encoding='utf-8') as archivo:
                lector = csv.DictReader(archivo)
                for fila in lector:
                    ids_existentes.append(int(fila['id']))
                    if fila['name'] == ipa:
                        ipa_encontrado = int(fila['id'])

            # Si encontramos el IPA, devolver su ID
            if ipa_encontrado is not None:
                return ipa_encontrado

        except Exception as e:
            print(f"Error al leer el archivo: {e}")
            return None
    else:
        print("El archivo no existe, se creará con el primer registro")

    # Si no existe el IPA, calcular el nuevo ID
    nuevo_id = max(ids_existentes) + 1 if ids_existentes else 1
    # print(f"Nuevo ID a asignar: {nuevo_id}")

    # Agregar el nuevo IPA al archivo CSV
    try:
        # Determinar si necesitamos escribir cabeceras (archivo vacío o no existe)
        escribir_cabeceras = not ids_existentes

        with open(archivo_csv, 'a', newline='', encoding='utf-8') as archivo, open(output_file, "a", encoding="utf-8") as outfile:
            escritor = csv.DictWriter(archivo, fieldnames=['id', 'name'])

            # Escribir cabeceras solo si es necesario
            if escribir_cabeceras:
                escritor.writeheader()

            # Escribir la nueva fila
            escritor.writerow({'id': nuevo_id, 'name': ipa})

            outfile.write("insert into sound_ipa (nuevo_id,name) values\n")
            outfile.write(f"({nuevo_id}, {ipa});\n\n")

        return nuevo_id

    except Exception as e:
        print(f"Error al escribir en el archivo: {e}")
        return None

def wiktionary_jsonl_postgresql_txt_words(input_file, output_file, search_words, search_word_lang_code):
    """
    Procesa TODAS las entradas que coincidan con la palabra buscada
    """
    with open(input_file, "r", encoding="utf-8") as infile, \
         open(output_file, "a", encoding="utf-8") as outfile:

        found_count = 0
        global last_word_id
        global last_word_sense_id
        global last_word_declension_non_exist_id
        global last_word_declension_irregular_id
        # current_word_id = last_word_id
        # current_sense_id = last_word_sense_id

        for line in infile:
            entry = json.loads(line)
            word_name = entry.get("word", "")
            lang_code = entry.get("lang_code", "")

            # search_word_names = [word.name for word in search_words]
            if word_name in search_words and lang_code == search_word_lang_code:
                word = create_word_with_name(word_name)
                print(entry)
                found_count += 1
                last_word_id += 1

                pos = entry.get("pos", "")
                pos_title=entry.get("pos_title","")
                if(is_forme_word(pos_title)):
                    continue




                # language_id = 0
                if search_word_lang_code == 'es':
                    word.language_id = 2
                else:
                    word.language_id = 1


                tags=entry.get("tags",[])
                
                word.part_speech_id=get_part_speech_id(pos,search_word_lang_code,entry)
                if word.part_speech_id==0:
                    continue
                throw_exception_tags_unknown(tags,word,entry)
                get_part_speech_sub_types(word, pos_title, search_word_lang_code, tags)
                word.gender_canonical_id=get_gender_canonical_id(tags,search_word_lang_code)

                # isInvariable=False
                word.is_invariable=get_is_invariable(tags)

                isOnlyPlural=False
                isOnlyPlural=get_is_only_plural(tags)

                # set_word_info_tags(word, tags)
                forms=entry.get("forms",[])
                get_word_declension_non_exist(word, forms, tags)
                print(forms)

                get_word_declension_irregular(word, tags, forms)
                # if not isInvariable:



                # Escribir la entrada de word

                # if(get_gender_canonical_id==0):
                #     outfile.write("insert into word (id, name, language_id, part_speech_id, part_speech_sub_type_id, isInvariable) values\n")
                #     outfile.write(f"({current_word_id}, '{word}', {language_id}, {pos_id}, {pos_sub_id}, {isInvariable});\n\n")
                # else:
                #     outfile.write("insert into word (id, name, language_id, part_speech_id, part_speech_sub_type_id, gender_canonical_id, isInvariable) values\n")
                #     outfile.write(f"({current_word_id}, '{word}', {language_id}, {pos_id}, {pos_sub_id}, {gender_canonical_id}, {isInvariable});\n\n")



                # ipa_sound_word_id_list=[]
                # for sound_obj in entry.get("sounds", []):
                #     ipa_raw = sound_obj.get("ipa") if isinstance(sound_obj, dict) else sound_obj
                #     if not ipa_raw:
                #         continue
                #     ipa_norm = normalize_ipa(ipa_raw)
                #     if not ipa_norm:
                #         continue
                #     ipa_sound_id=obtener_id_por_ipa(ipa_norm,sound_csv, output_file)
                #     if(ipa_sound_id not in ipa_sound_word_id_list):
                #         ipa_sound_word_id_list.append(ipa_sound_id)


                # for ipa_sound_id in ipa_sound_word_id_list:
                #     last_word_sound_ip_id+=1
                #     outfile.write("insert into word_sound_ipa (id, word_id, sound_ipa_id) values\n")
                #     outfile.write(f"({last_word_sound_ip_id}, {current_word_id}, {ipa_sound_id});\n\n")
                    # last_word_sound_ip_id+=1
                    # outfile.write("insert into word_sound_ipa (id, word_id, sound_ipa_id) values\n")
                    # outfile.write(f"({last_word_sound_ip_id}, {current_word_id}, {ipa_sound_id});\n\n")

                # Procesar todas las definiciones/sentidos
                order_sense=0
                for sense in entry.get("senses", []):
                    glosses = sense.get("glosses", [])
                    for gloss in glosses:
                        last_word_sense_id += 1
                        order_sense+=1
                        # Escapar comillas simples para SQL
                        safe_gloss = gloss.replace("'", "''")
                        word.senses.append(WordSense(last_word_sense_id,safe_gloss,order_sense))
                        # outfile.write("insert into word_sense (id, sense, word_id) values\n")
                        # outfile.write(f"({current_sense_id}, {current_word_id}, '{safe_gloss}');\n\n")
                print(word)
                if(word.gender_canonical_id==0):
                    outfile.write("insert into word (id, name, language_id, part_speech_id, isInvariable) values\n")
                    outfile.write(f"({last_word_id}, '{word.name}', {word.language_id}, {word.part_speech_id}, {word.is_invariable});\n\n")
                else:
                    outfile.write("insert into word (id, name, language_id, part_speech_id, gender_canonical_id, isInvariable) values\n")
                    outfile.write(f"({last_word_id}, '{word.name}', {word.language_id}, {word.part_speech_id}, {word.gender_canonical_id}, {word.is_invariable});\n\n")

                for word_sense in word.senses:
                    outfile.write("insert into word_sense (id, sense, word_id) values\n")
                    outfile.write(f"({last_word_sense_id}, {word_sense.sense}, {last_word_id}');\n\n")

                if not word.has_masculine_singular:
                    last_word_declension_non_exist_id+=1
                    outfile.write("insert into word_declension_non_exist (id,  word_id, gender_id, number) values\n")
                    outfile.write(f"({last_word_declension_non_exist_id}, {last_word_id}, 3,1);\n\n")

                if not word.has_masculine_plural:
                    last_word_declension_non_exist_id+=1
                    outfile.write("insert into word_declension_non_exist (id,  word_id, gender_id, number) values\n")
                    outfile.write(f"({last_word_declension_non_exist_id}, {last_word_id}, 3,2);\n\n")

                if not word.has_femenine_singular:
                    last_word_declension_non_exist_id+=1
                    outfile.write("insert into word_declension_non_exist (id,  word_id, gender_id, number) values\n")
                    outfile.write(f"({last_word_declension_non_exist_id}, {last_word_id}, 2,1);\n\n")

                if not word.has_femenine_plural:
                    last_word_declension_non_exist_id+=1
                    outfile.write("insert into word_declension_non_exist (id,  word_id, gender_id, number) values\n")
                    outfile.write(f"({last_word_declension_non_exist_id}, {last_word_id}, 2,2);\n\n")


                for word_declension_irregular in word.word_declension_irregular_list:
                    outfile.write("insert into word_declension_irregular (id,  word_id, gender_id, number_id,name) values\n")
                    outfile.write(f"({last_word_declension_irregular_id}, {last_word_id}, {word_declension_irregular.gender_id},{word_declension_irregular.number_id},{word_declension_irregular.name});\n\n")

        if found_count == 0:
            outfile.write(f"No se encontró: {search_words} ({search_word_lang_code})\n")
        else:
            outfile.write(f"-- Procesadas {found_count} entradas para '{search_words}' ({search_word_lang_code})\n")

        # print(f"Proceso completado. Encontradas {found_count} entradas.")
        return found_count

def get_part_speech_id(pos, language_code,entry):
    match language_code:
        case 'fr':
            return get_part_speech_fr_id(pos,entry)
        case 'es':
            return get_part_speech_es_id(pos)


def get_part_speech_fr_id(pos,entry):
    match pos:
        case 'noun':
            return 1
        case 'verb':
            return 2
        case 'adv':
            return 4
        case 'pron':
            return 5
        case 'prep':
            return 6
        case 'conj':
            return 7
        case 'intj':
            return 8
        case 'adj':
            return 3
        case 'article':
            return 10
        case 'character':
            return 11
        # simbolos como km se omiten
        case 'symbol':
            return 0
        case _:
            raise ValueError(f"Part_sub_speech desconocido: '{pos}'")
            return 0

def get_part_speech_es_id(pos):
    return 0


def get_part_speech_sub_types(word, pos_title, language_code, tags):
    match language_code:
        case 'fr':
            return get_part_speech_sub_types_fr(word,pos_title, tags)
        case 'es':
            return get_part_speech_sub_type_es_id(pos_title)


def get_part_speech_sub_types_fr(word,pos_title,tags):
    if 'intransitive' in tags and word.part_speech_id==2:
        word.part_speech_sub_types.append(9)
    if 'pronominal' in tags and word.part_speech_id==2:
        word.part_speech_sub_types.append(10)
    if 'transitive' in tags and word.part_speech_id==2:
        word.part_speech_sub_types.append(11)
    if 'coordinating' in tags and word.part_speech_id==7:
        word.part_speech_sub_types.append(14)
    if 'comparative' in tags and word.part_speech_id==7:
        word.part_speech_sub_types.append(15)
    if 'impersonal' in tags and word.part_speech_id==5:
        word.part_speech_sub_types.append(17)
    

    if('Pronom personnel' in pos_title):
        word.part_speech_sub_types.append(1)
    elif('Article défini' in pos_title):
        word.part_speech_sub_types.append(1)
    elif('Article indéfini' in pos_title):
        word.part_speech_sub_types.append(3)
    elif('Nom commun' in pos_title):
        word.part_speech_sub_types.append(5)
    elif('Conjonction de coordination' in pos_title):
        word.part_speech_sub_types.append(4)
    elif('Pronom indéfini' in pos_title):
        word.part_speech_sub_types.append(6)
    elif('Article partitif' in pos_title):
        word.part_speech_sub_types.append(7)
    elif('Lettre' in pos_title):
        word.part_speech_sub_types.append(8)
    elif('Pronom relatif' in pos_title):
        word.part_speech_sub_types.append(12)
    elif('Pronom interrogatif' in pos_title):
        word.part_speech_sub_types.append(12)
    elif('Pronom démonstratif' in pos_title):
        word.part_speech_sub_types.append(16)

    elif('Forme de verbe' in pos_title or 'Forme de nom commun' in pos_title or 'Forme d’article défini' in pos_title or 'Forme d’adjectif numéral' in pos_title or 'Forme d’adjectif' in pos_title
         or 'Forme d’article indéfini' in pos_title or 'Forme de pronom indéfini' in pos_title):
        return
    elif('Adjectif' in pos_title or 'Interjection' in pos_title or 'Préposition' in pos_title or 'Verbe' in pos_title
         or 'Conjonction' in pos_title or 'Adverbe' in pos_title):
        return
    else:
        raise ValueError(f"Part_sub_speech desconocido: '{pos_title}'")


def get_part_speech_sub_type_es_id(pos_title):
    return 0

def is_forme_word(pos_title):
    if('Forme de verbe' in pos_title or 'Forme de nom commun' in pos_title or 'Forme d’article défini' in pos_title or 'Forme d’adjectif numéral' in pos_title or 'Forme d’adjectif' in pos_title
         or 'Forme d’article indéfini' in pos_title or 'Forme de pronom indéfini' in pos_title):
        return True
    return False


# def get_gender_canonical_id(tags, language_code):
#     match language_code:
#         case 'fr':
#             return get_gender_canonical_fr_id(tags)
#         case 'es':
#             return get_gender_canonical_es_id(tags)

def get_gender_canonical_id(tags, language_code):
    match language_code:
        case 'fr':
            if 'neuter' in tags:
                return 1
            if 'masculine' in tags:
                return 3
            if 'feminine' in tags:
                return 2
        case 'es':
            if 'masculine' in tags:
                return 3
            if 'feminine' in tags:
                return 2
    return 0

def get_gender_canonical_fr_id(tags):
    if 'masculine' in tags:
        return 3
    if 'feminine' in tags:
        return 2
    return 0

def get_gender_canonical_es_id(tags):
    return 0

def get_is_invariable(tags):
    if 'invariable' in tags:
        return True
    return False

def get_is_only_plural(tags):
    if 'plural-only' in tags:
        return True
    return False

# def set_word_info_tags(word, tags):
#     if 'intransitive' in tags and word.part_speech_id==1:
#         word.part_speech_sub_type_id=9

def get_word_declension_non_exist(word,  forms, tags):
    # word_declension_non_exist=[]
    # id=word_declension_non_exist_last_id
    if word.is_invariable:
        # if 'femenine' not in tags and 'masculine' not in tags:
        if 'femenine' not in tags and 'masculine' in tags:
            word.has_femenine_singular=False
            word.has_femenine_plural=False
        if 'masculine' not in tags and 'femenine' in tags:
            word.has_masculine_singular=False
            word.has_masculine_plural=False
        if 'only-singular' in tags or 'singular' in tags and 'plural' not in tags:
            word.has_femenine_plural=False
            word.has_masculine_plural=False
        if 'only-plural' in tags or 'plural' in tags and 'singular' not in tags:
            word.has_femenine_singular=False
            word.has_masculine_singular=False
    elif word.part_speech_id in (1,3,5,10) and 'masculine' in tags and 'femenine' in tags:
        if 'plural' in tags:
            word.has_masculine_plural=True
            word.has_femenine_plural=True
        else:
            word.has_masculine_singular=True
            word.has_femenine_singular=True
    elif word.part_speech_id==1:
        if word.gender_canonical_id==2:
            word.has_masculine_singular=False
            word.has_mascuine_plural=False
            word.has_femenine_singular=True
            word.has_femenine_plural=False
            for form in forms:
                tags=form.get("tags",[])
                if 'plural' in tags:
                    word.has_femenine_plural = True
        elif word.gender_canonical_id==3:
            word.has_masculine_singular=True
            word.has_mascuine_plural=False
            word.has_femenine_singular=False
            word.has_femenine_plural=False
            for form in forms:
                tags=form.get("tags",[])
                if 'plural' in tags:
                    word.has_mascuine_plural = True
    elif word.part_speech_id ==2:
        return
    elif word.part_speech_id in (3,5,10):
        if word.gender_canonical_id==2:
            word.has_femenine_singular=True
        elif word.gender_canonical_id==3:
            word.has_masculine_singular=True
        for form in forms:
            tags=form.get("tags",[])
            if 'singular' in tags and 'masculine' in tags:
                word.has_masculine_singular=True
            elif 'plural' in tags and 'masculine' in tags:
                word.has_masculine_plural=True
            elif 'singular' in tags and 'feminine' in tags:
                word.has_femenine_singular=True
            elif 'plural' in tags and 'feminine' in tags:
                word.has_femenine_plural=True
            elif 'feminine' in tags and not 'plural' in tags and not 'singular' in tags:
                word.has_femenine_singular=True
            elif 'masculine' in tags and not 'plural' in tags and not 'singular' in tags:
                word.has_masculine_singular=True







def get_word_declension_irregular(word, tags, forms):
    # aqui se controla si es neutro, el cual se considera como irregular
    # if word.gender_canonical_id==1:

    global last_word_declension_irregular_id
    if word.is_invariable:
        return
    if word.part_speech_id==1:
        if word.has_masculine_plural or word.has_femenine_plural:
            plural_regular = convert_word_singular_to_plural_fr(word.name)
            for form in forms:
                tags=form.get("tags",[])
                if 'plural' in tags:
                    form_plural= form.get("form","")
                    if plural_regular != form_plural:
                        last_word_declension_irregular_id+=1
                        word_declension_irregular=WordDeclensionIrregular(last_word_declension_irregular_id,word.id,1,1,form_plural)
                        word.word_declension_irregular_list.append(word_declension_irregular)
    elif word.part_speech_id in (3,5,10):
        for form in forms:
            tags=form.get("tags",[])
            if word.has_masculine_singular and 'singular' in tags and 'masculine' in tags:
                regular_form=convert_word_feminine_to_masculine_fr(word.name)
                form_real= form.get("form","")
                if regular_form!=form_real:
                    last_word_declension_irregular_id+=1
                    word_declension_irregular=WordDeclensionIrregular(last_word_declension_irregular_id,word.id,3,1,form_real)
                    word.word_declension_irregular_list.append(word_declension_irregular)
            elif word.has_masculine_plural and 'plural' in tags and 'masculine' in tags:
                regular_form=convert_word_feminine_to_masculine_fr(word.name)
                form_real= form.get("form","")
                if regular_form!=form_real:
                    last_word_declension_irregular_id+=1
                    word_declension_irregular=WordDeclensionIrregular(last_word_declension_irregular_id,word.id,3,2,form_real)
                    word.word_declension_irregular_list.append(word_declension_irregular)
            elif word.has_femenine_singular and 'singular' in tags and 'feminine' in tags:
                regular_form=convert_word_feminine_to_masculine_fr(word.name)
                form_real= form.get("form","")
                if regular_form!=form_real:
                    last_word_declension_irregular_id+=1
                    word_declension_irregular=WordDeclensionIrregular(last_word_declension_irregular_id,word.id,2,1,form_real)
                    word.word_declension_irregular_list.append(word_declension_irregular)
            elif  word.has_femenine_plural and'plural' in tags and 'feminine' in tags:
                regular_form=convert_word_feminine_to_masculine_fr(word.name)
                form_real= form.get("form","")
                if regular_form!=form_real:
                    last_word_declension_irregular_id+=1
                    word_declension_irregular=WordDeclensionIrregular(last_word_declension_irregular_id,word.id,2,2,form_real)
                    word.word_declension_irregular_list.append(word_declension_irregular)




def throw_exception_tags_unknown(tags, word,entry):
    if len(tags)==0 and word.part_speech_id!=2 and word.part_speech_id!=4 and word.part_speech_id!=7 and word.part_speech_id!=8:
        raise ValueError("No hay tags")
    if word.part_speech_id==1 and 'singular' in tags and 'plural' in tags and 'invariable' not in tags:
        raise ValueError("Vigilar porque en un noun se señala si es plural o singular")
    if word.part_speech_id in (3,5,10) and 'masculine' in tags and 'feminine' in tags:
        raise ValueError("Vigilar porque en un  se señala si es plural o singular")
#, 'partial'
    valid_tags = {'masculine', 'feminine', 'coordinating','accusative', 'invariable','definite', 
                  'plural-only','singular-only','singular','person', 'neuter', 'indefinite', 'letter', 'intransitive', 'pronominal', 'transitive',
                  'relative', 'interrogative', 'partial', 'comparative', 'demonstrative', 'impersonal', 'plural', 'dative', 'indirect'}

    for tag in tags:
        if tag not in valid_tags:
            raise ValueError(f"Tag desconocido: '{tag}'. en word {word}")

# wiktionary_jsonl_postgresql_txt_words(fr_extract,output_file_txt, create_word_with_name_list('bon'), 'fr', 50 ,208,0)

# def set_word_gender_number_regular(word, gender_base, number_base, gender_target,number_target, language_code):
#     match language_code:
#         case 'fr':
#             return set_word_gender_number_regular_fr(word, gender_base, number_base, gender_target,number_target)

# def set_word_gender_number_regular_fr(word, gender_base, number_base, gender_target,number_target):
#     # match gender_base:
#         return 0

def convert_word_masculine_to_feminine_fr(word):
    if word.endswith('e'):
        return word
    elif word.endswith('é'):
        return word+'e'
    elif word.endswith('eur'):
        return word[:-1]+'se'
    elif word.endswith('eux'):
        return word[:-1]+'se'
    elif word.endswith('ien'):
        return word+'ne'
    elif word.endswith('ion'):
        return word+'ne'
    elif word.endswith('er'):
        return word[:-2]+'ère'
    elif word.endswith('if'):
        return word[:-2] +'ive'
    else:
        return word+'e'

def convert_word_feminine_to_masculine_fr(word):
    if word.endswith('e'):
        return word
    elif word.endswith('é'):
        return word+'e'
    elif word.endswith('eur'):
        return word[:-1]+'se'
    elif word.endswith('eux'):
        return word[:-1]+'se'
    elif word.endswith('ien'):
        return word+'ne'
    elif word.endswith('ion'):
        return word+'ne'
    elif word.endswith('er'):
        return word[:-2]+'ère'
    elif word.endswith('if'):
        return word[:-2] +'ive'
    else:
        return word+'e'

def convert_word_singular_to_plural_fr(word):
    if word.endswith('s') or word.endswith('x') or word.endswith('z'):
        return word
    elif word.endswith('eau') or word.endswith('au') or word.endswith('eu'):
        return word+'x'
    else:
        return word+'s'


# print(convert_word_masculine_to_feminine_fr('sportif'))

def create_word_with_name(word_name):
    return Word(0,word_name, 0, 0,[], False, False, False, False, False, 0, [], [])

# def create_word_with_name_list(word_name_list):
#     words =[]
#     for word_name in word_name_list:
#         words.append(create_word_with_name(word_name))
#     return words

wiktionary_jsonl_postgresql_txt_words(fr_extract, output_file_txt,['la','le','et','à','aller','ça','faire','on','pour','dire','pouvoir','qui','vouloir','ce','mais','me','dans','savoir','du','bien','que','plus','non',
                                                                   'que','plus','non','te','mon','au','avec','moi','devoir','oui','tout','se','venir',
'toi','ici','rien','ma','comme','lui','où','si','là','suivre','parler','prendre',
'cette','votre','quand','alors','chose','par','ton','croire','falloir',
'très','ou','quoi','passer','penser','aussi','jamais','attendre','pourquoi','trouver',
'laisser','sa','ta','arriver','ces','donner','regarder','encore'] , 'fr')
# ['la','le','et','à','aller','ça','faire','on','une','pour','des','dire','pouvoir','qui','vouloir','ce','mais','me','dans','savoir','du','y','bien','voir','que','plus','non']

# https://pequesfrançais.com/formacion-del-femenino/
# print(obtener_id_por_ipa('dasda1',sound_csv))

# por separado les, un,une,des, voir, y,son,sur, bon


# ['la','le','et','à','un','aller','ça','faire','les','on','une','pour','des','dire']
# 'pouvoir','qui','vouloir','ce','mais','me','dans','savoir','du','y','bien','voir','que','plus','non'

# 'que','plus','non','te','mon','au','avec','moi','devoir','oui','tout','se','venir','sur',
# 'toi','ici','rien','ma','comme','lui','où','si','là','suivre','parler','prendre',
# 'cette','votre','quand','alors','chose','par','son','ton','croire','falloir',
# 'très','ou','quoi','bon','passer','penser','aussi','jamais','attendre','pourquoi','trouver',
# 'laisser','sa','ta','arriver','ces','donner','regarder','encore'