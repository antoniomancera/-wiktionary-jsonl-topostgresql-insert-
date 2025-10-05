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
last_word_declension_variation_id=0

word_unable_to_convert_list=[]



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
        global last_word_declension_variation_id
      

        for line in infile:
            entry = json.loads(line)
            word_name = entry.get("word", "")
            lang_code = entry.get("lang_code", "")

            # search_word_names = [word.name for word in search_words]
            if word_name in search_words and lang_code == search_word_lang_code:
                word = Word.create_word_with_name(word_name)
                # print(entry)
                found_count += 1
                # last_word_id += 1

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
                word.gender_canonical_id=get_gender_canonical_id(word,tags,search_word_lang_code)
                word.number_canonical_id = get_number_canonical_id(word, tags, search_word_lang_code)

                # isInvariable=False
                word.is_invariable=get_is_invariable(tags)

                # set_word_info_tags(word, tags)
                forms=entry.get("forms",[])
                get_word_declension_non_exist(word, forms, tags)
                # print(forms)

                get_word_declension_irregular(word, tags, forms)
                # if not isInvariable:

                if word.is_impossible_convert_postgresql:
                    order_sense=0
                    for sense in entry.get("senses", []):
                        glosses = sense.get("glosses", [])
                        first_safe_gloss = glosses[0].replace("'", "''")
                        outfile.write(f"({word.name} con part_speech '{word.part_speech_id}' y con primer sense, {first_safe_gloss},da errores,comporobar);\n\n")

                else:
                    order_sense=0
                    for sense in entry.get("senses", []):
                        glosses = sense.get("glosses", [])
                        for gloss in glosses:
                            last_word_sense_id += 1
                            order_sense+=1
                        
                            safe_gloss = gloss.replace("'", "''")
                            word.senses.append(WordSense(last_word_sense_id,safe_gloss,order_sense))

                last_word_id+=1
                # print(word)
                print(last_word_id)
                # if last_word_id>100:
                #     break
                if word.part_speech_id not in (1,3,5,10):
                    outfile.write("insert into word (id, name, language_id, part_speech_id, level_id) values\n")
                    outfile.write(f"({last_word_id}, '{word.name}', {word.language_id}, {word.part_speech_id}, 1);\n\n")
                else:
                    outfile.write("insert into word (id, name, language_id, part_speech_id, level_id, gender_canonical_id, number_canonical_id, isDeclensionRegular) values\n")
                    isDeclensionRegular = True
                    if word.is_invariable or not word.has_masculine_singular or not word.has_masculine_plural or not word.has_femenine_singular or not word.has_femenine_plural or word.is_only_singular or word.is_only_plural or len(word.word_declension_irregular_list)>0:
                        isDeclensionRegular = False

                    outfile.write(f"({last_word_id}, '{word.name}', {word.language_id}, {word.part_speech_id}, 1, {word.gender_canonical_id}, {word.number_canonical_id}, {isDeclensionRegular});\n\n")

                    if not isDeclensionRegular:
                        last_word_declension_variation_id+=1
                        outfile.write("insert into word_declension_variation (id, word_id, isInvariable) values\n")
                        outfile.write(f"({last_word_declension_variation_id}, '{last_word_id}', {word.is_invariable});\n\n")

                        if not word.has_masculine_singular:
                            last_word_declension_non_exist_id+=1
                            outfile.write("insert into word_declension_non_exist (id,  word_iword_declension_variation_idd, gender_id, number) values\n")
                            outfile.write(f"({last_word_declension_non_exist_id}, {last_word_declension_variation_id}, 3,1);\n\n")

                        if not word.has_masculine_plural:
                            last_word_declension_non_exist_id+=1
                            outfile.write("insert into word_declension_non_exist (id,  word_declension_variation_id, gender_id, number) values\n")
                            outfile.write(f"({last_word_declension_non_exist_id}, {last_word_declension_variation_id}, 3,2);\n\n")

                        if not word.has_femenine_singular:
                            last_word_declension_non_exist_id+=1
                            outfile.write("insert into word_declension_non_exist (id,  word_declension_variation_id, gender_id, number) values\n")
                            outfile.write(f"({last_word_declension_non_exist_id}, {last_word_declension_variation_id}, 2,1);\n\n")

                        if not word.has_femenine_plural:
                            last_word_declension_non_exist_id+=1
                            outfile.write("insert into word_declension_non_exist (id,  word_declension_variation_id, gender_id, number) values\n")
                            outfile.write(f"({last_word_declension_non_exist_id}, {last_word_declension_variation_id}, 2,2);\n\n")

                        for word_declension_irregular in word.word_declension_irregular_list:
                            last_word_declension_irregular_id+=1
                            outfile.write("insert into word_declension_irregular (id,  word_declension_variation_id, gender_id, number_id,name) values\n")
                            outfile.write(f"({last_word_declension_irregular_id}, {last_word_declension_variation_id}, {word_declension_irregular.gender_id},{word_declension_irregular.number_id},{word_declension_irregular.name});\n\n")


                for word_sense in word.senses:
                    last_word_sense_id+=1
                    outfile.write("insert into word_sense (id, sense, word_id, order) values\n")
                    outfile.write(f"({last_word_sense_id}, {word_sense.sense}, {last_word_id}, {word_sense.sense});\n\n")

                


                
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
        case 'typographic variant':
            return 0
        case _:
            # raise ValueError(f"Part_sub_speech desconocido: '{pos}'")
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
         or 'Forme d’article indéfini' in pos_title or 'Forme de pronom indéfini' in pos_title or 'Forme' in pos_title):
        word.is_impossible_convert_postgresql=True
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


def get_gender_canonical_id(word,tags, language_code):
    if word.part_speech_id not in (1,3,5,10):
        return 0
    match language_code:
        case 'fr':
            if 'neuter' in tags:
                return 1
            if 'masculine' in tags:
                return 3
            if 'feminine' in tags:
                return 2
            return 3
        case 'es':
            if 'masculine' in tags:
                return 3
            if 'feminine' in tags:
                return 2
    return 0

def get_number_canonical_id(word, tags, language_code):
    if word.part_speech_id not in (1,3,5,10):
        return 0
    match language_code:
        case 'fr':
            if 'singular' in tags or 'singular-only':
                return 1
            if 'plural' in tags or 'only-plural':
                return 2
        case 'es':
            if 'masculine' in tags:
                return 3
            if 'feminine' in tags:
                return 2

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

def get_word_declension_non_exist(word,  forms, tags):
    if word.is_impossible_convert_postgresql:
        return
    
    tag_valid={'feminine','masculine','singular-only','singular','invariable', 'plural-only', 'plural', 'person', 'definite', 'indefinite'}
    
    if word.part_speech_id in (1,3,5,10):
        for tag in tags:
            if tag not in tag_valid:
                word.is_impossible_convert_postgresql=True
                add_word_unable_to_convert_list(word)
                return
        if 'invariable' in tags:
            if 'feminine' in tags:
                if 'singular' in tags or 'singular-only' in tags:
                    word.has_femenine_singular=True
                elif 'plural' in tags or 'only-plural' in tags:
                    word.has_femenine_plural=True
            if 'masculine' in tags:
                if 'singular' in tags:
                    word.has_masculine_singular=True
                elif 'plural' in tags:
                    word.has_masculine_plural=True
            if 'singular-only' in tags:
                word.has_femenine_plural=False
                word.has_masculine_plural=False
            if 'only-plural' in tags:
                word.has_femenine_singular=False
                word.has_masculine_singular=False
        else:
            if 'singular' not in tags and 'plural' not in tags:
                if 'feminine' in tags:
                    word.has_femenine_singular=True
                elif 'masculine' in tags:
                    word.has_masculine_singular=True
                else:
                    add_word_unable_to_convert_list(word)
            if 'singular' in tags or 'singular-only' in tags:
                if 'feminine' in tags:
                    word.has_femenine_singular=True
                elif 'masculine' in tags:
                    word.has_masculine_singular=True
                else:
                    add_word_unable_to_convert_list(word)
                    
            elif 'plural' in tags or 'only-plural' in tags:
                if 'feminine' in tags:
                    word.has_femenine_plural=True
                elif 'masculine' in tags:
                    word.has_masculine_plural=True
                else:
                    add_word_unable_to_convert_list(word)
            
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
                # en el caso en que haya un form que no tengo ni plural ni singular, y que no sea 
                # singular-only se considera que es la forma plural
                elif 'feminine' in tags and not 'plural' in tags and not 'singular' in tags and not 'only-plural' in tags:
                    word.has_femenine_singular=True
                elif 'masculine' in tags and not 'plural' in tags and not 'singular' in tags and not 'only-plural' in tags:
                    word.has_masculine_singular=True
                # en el caso en que haya un form que no tengo ni plural ni singular, y que no sea 
                # only-singular se considera que es la forma plural
                elif 'feminine' in tags and not 'plural' in tags and not 'singular' in tags and not 'singular-only' in tags:
                    word.has_femenine_plural=True
                elif 'masculine' in tags and not 'plural' in tags and not 'singular' in tags and not 'singular-only' in tags:
                    word.has_masculine_plural=True
                # si hay uno con plural pero no hay genero se entiende que es el plural de la forma canonica
                elif 'plural' in tags and 'feminine' not in tags and 'masculine' not in tags:
                    if word.gender_canonical_id==2:
                        word.has_femenine_plural=True
                    if word.gender_canonical_id==3:
                        word.has_masculine_plural=True







def get_word_declension_irregular(word, global_tags, forms):
    if word.is_impossible_convert_postgresql:
        return
    global last_word_declension_irregular_id
    if word.part_speech_id in (1,3,5,10):
        if  not word.is_invariable:
            for form in forms:
                form_tags=form.get("tags",[])
                # buscamos si existe una forma femenina y singular
                if 'feminine' in form_tags and 'singular' in form_tags or 'feminine' in form_tags and 'singular' not in form_tags and 'plural' not in form_tags and word.has_femenine_singular:
                    if word.gender_canonical_id==3 and word.number_canonical_id==1:
                        regular_form=convert_word_masculine_to_feminine_fr(word.name)
                        form_real= form.get("form","")
                        if regular_form!=form_real:
                            last_word_declension_irregular_id+=1
                            word_declension_irregular=WordDeclensionIrregular(last_word_declension_irregular_id,word.id,2,1,form_real)
                            word.word_declension_irregular_list.append(word_declension_irregular)
                    else:
                        word.is_impossible_convert_postgresql=True
                elif 'masculine' in form_tags and 'singular' in form_tags or 'masculine' in form_tags and 'singular' not in form_tags and 'plural' not in form_tags and word.has_masculine_singular:
                    if word.gender_canonical_id==2 and word.number_canonical_id==1:
                        regular_form=convert_word_feminine_to_masculine_fr(word.name)
                        form_real= form.get("form","")
                        if regular_form!=form_real:
                            last_word_declension_irregular_id+=1
                            word_declension_irregular=WordDeclensionIrregular(last_word_declension_irregular_id,word.id,2,1,form_real)
                            word.word_declension_irregular_list.append(word_declension_irregular)
                    else:
                        word.is_impossible_convert_postgresql=True  
                # si no tiene genero pero pone plural, es porque es el polura de la forma canonica
                elif 'plural' in form_tags and 'feminine' not in form_tags and 'masculine' not in form_tags and 'singular-only' not in global_tags:
                    plural_regular = convert_word_singular_to_plural_fr(word.name)
                    plural_form_actual= form.get("form","")
                    if plural_regular != plural_form_actual:
                                last_word_declension_irregular_id+=1
                                word_declension_irregular=WordDeclensionIrregular(last_word_declension_irregular_id,word.id,word.gender_canonical_id,1,plural_form_actual)
                                word.word_declension_irregular_list.append(word_declension_irregular)


                elif 'feminine' in form_tags and 'plural' in form_tags:
                    if word.gender_canonical_id==2 and word.number_canonical_id==1:
                        plural_femenine_regular = convert_word_singular_to_plural_fr(word.name)
                        plural_form_actual= form.get("form","")
                        if plural_femenine_regular != plural_form_actual:
                                    last_word_declension_irregular_id+=1
                                    word_declension_irregular=WordDeclensionIrregular(last_word_declension_irregular_id,word.id,2,2,plural_form_actual)
                                    word.word_declension_irregular_list.append(word_declension_irregular)
                    elif word.gender_canonical_id==3 and word.number_canonical_id==1:
                        plural_femenine_regular = convert_word_singular_to_plural_fr(convert_word_masculine_to_feminine_fr(word.name))
                        plural_form_actual= form.get("form","")
                        if plural_femenine_regular != plural_form_actual:
                                    last_word_declension_irregular_id+=1
                                    word_declension_irregular=WordDeclensionIrregular(last_word_declension_irregular_id,word.id,2,2,plural_form_actual)
                    else:
                        word.is_impossible_convert_postgresql=True  


                elif 'masculine' in form_tags and 'plural' in form_tags:
                    if word.gender_canonical_id==2 and word.number_canonical_id==1:
                        plural_masculine_regular = convert_word_singular_to_plural_fr(convert_word_feminine_to_masculine_fr(word.name))
                        plural_form_actual= form.get("form","")
                        if plural_masculine_regular != plural_form_actual:
                                    last_word_declension_irregular_id+=1
                                    word_declension_irregular=WordDeclensionIrregular(last_word_declension_irregular_id,word.id,2,1,plural_form_actual)
                                    word.word_declension_irregular_list.append(word_declension_irregular)
                    elif word.gender_canonical_id==3 and word.number_canonical_id==1:
                        plural_masculine_regular = convert_word_singular_to_plural_fr(word.name)
                        plural_form_actual= form.get("form","")
                        if plural_masculine_regular != plural_form_actual:
                                    last_word_declension_irregular_id+=1
                                    word_declension_irregular=WordDeclensionIrregular(last_word_declension_irregular_id,word.id,2,1,plural_form_actual)
                    else:
                        word.is_impossible_convert_postgresql=True  
                elif len(form_tags)>0:
                    word.is_impossible_convert_postgresql=True




def throw_exception_tags_unknown(tags, word,entry):
    if len(tags)==0 and word.part_speech_id in (1,3,5,10):
        word.is_impossible_convert_postgresql=True
        # raise ValueError("No hay tags")
        return
    if len(tags)>0 and word.part_speech_id in (1,3,5,10) and 'masculine' not in tags and 'feminine' not in tags:
        word.is_impossible_convert_postgresql=True
    # if word.part_speech_id==1 and 'singular' in tags and 'plural' in tags and 'invariable' not in tags:
    #     raise ValueError("Vigilar porque en un noun se señala si es plural o singular")
    # if word.part_speech_id in (3,5,10) and 'masculine' in tags and 'feminine' in tags:
    #     raise ValueError("Vigilar porque en un  se señala si es plural o singular")
#, 'partial'
    valid_tags = {'masculine', 'feminine', 'coordinating','accusative', 'invariable','definite', 
                  'plural-only','singular-only','singular','person', 'indefinite', 'letter', 'intransitive', 'pronominal', 'transitive',
                  'relative', 'interrogative', 'partial', 'comparative', 'demonstrative', 'impersonal', 'plural', 'dative', 'indirect'}

    for tag in tags:
        if tag not in valid_tags:
            word.is_impossible_convert_postgresql=True
            # raise ValueError(f"Tag desconocido: '{tag}'. en word {word}")
    return 0

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
    

def add_word_unable_to_convert_list(word):
    global word_unable_to_convert_list
    word_unable_to_convert_list.append(word)



wiktionary_jsonl_postgresql_txt_words(fr_extract, output_file_txt,['la','le','et','à','aller','ça','faire','on','pour','dire','pouvoir','qui','vouloir','ce','mais','me','dans','savoir','du','bien','que','plus','non',
                                                                   'que','plus','non','te','mon','au','avec','moi','devoir','oui','tout','se','venir',
'toi','ici','rien','ma','comme','lui','où','si','là','suivre','parler','prendre',
'cette','votre','quand','alors','chose','par','ton','croire','falloir',
'très','ou','quoi','passer','penser','aussi','jamais','attendre','pourquoi','trouver',
'laisser','sa','ta','arriver','ces','donner','regarder','encore','appeler','homme','partir','petit','mes',
'toujours','jour','femme','temps','maintenant','notre','vie','deux','mettre','rester','sans','arrêter','vraiment',
'connaître','sûr','merci','tuer','comment','mourir','demander','même','peut-être','dieu','fois','oh','père','peu',
'comprendre','seul','quelque','sortir','an','trop','chez','fille','aux',
    'monde', 'vrai', 'autre', 'besoin', 'accord', 'ses', 'ami', 'monsieur', 'enfant', 'entendre', 
    'voilà', 'chercher', 'heure', 'tes', 'aider', 'mère', 'déjà', 'beau', 'essayer', 'quel', 
    'juste', 'mieux', 'vos', 'grand', 'beaucoup', 'revenir', 'donc', 'plaire', 'maison', 
    'gens', 'après', 'nuit', 'personne', 'ah', 'soir', 'nom', 'bonjour', 'jouer', 'finir', 
    'peur', 'perdre', 'maman', 'sentir', 'ouais', 'rentrer', 'avant', 'nos', 'problème', 
    'argent', 'quelle', 'vivre', 'rendre', 'tenir', 'cet', 'main', 'cela', 'vite', 'oublier', 
    'air', 'depuis', 'fils', 'travailler', 'moins', 'tête', 'coup', 'écouter', 'raison', 'manger'], 'fr')



# , 
#     'mort', 'amour', 'mal', 'entrer', 'devenir', 'hein', 'commencer', 'moment', 'dernier', 'voiture', 
#     'demain', 'payer', 'tirer', 'ouvrir', 'oeil', 'fait', 'changer', 'question', 'tomber', 'assez', 
#     'foutre', 'excuser', 'affaire', 'dormir', 'combien', 'frère', 'travail', 'idée', 'eh', 'famille', 
#     'truc', 'trois', 'tant', 'ni', 'premier', 'tous', 'occuper', 'entre', 'marcher', 'chance', 
#      'envoyer', 'histoire', 'tard', 'apprendre', 'minute', 'boire', 'garder', 'quelques', 'type', 
#     'porte', 'montrer', 'mec', 'asseoir', 'fou', 'porter', 'année', 'sous', 'souvenir', 'prêt', 
#     'contre', 'prier', 'pendant', 'mois', 'servir', 'madame', 'putain', 'écrire', 'part', 'eau', 
#     'sang', 'place', 'espérer', 'désoler', 'jeune', 'eux', 'retrouver', 'ville', 'terre', 'gagner', 
#     'semaine', 'acheter', 'longtemps', 'gars', 'chambre', 'hé', 'côté', 'leur', 'vieux', 'rappeler', 
#     'lire', 'cas', 'mot', 'seulement', 'voici', 'salut', 'monter', 'désolé', 'quitter', 'police', 
#     'suite', 'matin', 'emmener', 'toucher', 'continuer', 'gros', 'enfin', 'mari', 'là-bas', 'revoir', 
#     'importer', 'papa', 'puis', 'train', 'manquer', 'raconter', 'ensemble', 'mauvais', 'film', 'répondre', 
#     'garçon', 'corps', 'celui', 'autres', 'heureux', 'loin', 'sauver', 'chaque', 'retourner', 'leurs', 
#     'rencontrer', 'coeur', 'voler', 'fermer', 'car', 'valoir', 'descendre', 'ok', 'feu', 'docteur', 
#     'suffire', 'façon', 'nouveau', 'important', 'sembler', 'compter', 'vers', 'joli', 'point', 'hier', 
#     'chien', 'dont', 'guerre', 'genre', 'merde', 'meilleur', 'marier', 'arme', 'cause', 'endroit', 
#     'ordre', 'poser', 'reste', 'pied', 'envie', 'fin', 'tiens', 'inquiéter', 'bouger', 'plutôt', 
#     'apporter', 'pardon', 'photo', 'plein', 'devant', 'décider', 'ainsi', 'droit', 'aucune', 'vendre', 
#     'école', 'cher', 'chef', 'tourner', 'cacher', 'boulot', 'pays', 'ceux', 'possible', 'expliquer', 
#     'battre', 'peine', 'livre', 'agir', 'imaginer', 'tour', 'adorer', 'vérité', 'recevoir', 'gentil', 
#     'jeter', 'pleurer', 'bébé', 'partie', 'nouvelle', 'jeu', 'amener', 'instant', 'parent', 'dur', 
#     'service', 'plaisir', 'promettre', 'mentir', 'soeur', 'bientôt', 'lit', 'tellement', 'utiliser', 'lieu', 
#     'coucher', 'presque', 'dehors', 'préférer', 'content', 'pauvre', 'offrir', 'roi', 'verre', 'réveiller', 
#     'aucun', 'aide', 'journée', 'préparer', 'numéro', 'permettre', 'ramener', 'enlever', 'chéri', 
#     'fort', 'lâcher', 'choisir', 'musique', 'conduire', 'faute', 'calmer', 'mariage', 'bureau', 'route', 
#     'chanter', 'disparaître', 'lever', 'présenter', 'accepter', 'sinon', 'long', 'café', 'propre', 'confiance', 
#     'cinq', 'bonsoir', 'compte', 'téléphone', 'casser', 'prochain', 'frapper', 'facile', 'attention', 'rêve', 
#     'copain', 'malade', 'rue', 'lettre', 'ignorer', 'fête', 'couper', 'esprit', 'super', 'taire', 
#     'seigneur', 'flic', 'parfois', 'capitaine', 'âge', 'autant', 'force', 'pièce', 'quatre', 'cul', 
#     'difficile', 'bras', 'tromper', 'surtout', 'ressembler', 'jurer', 'plan', 'prison', 'sale', 'courir', 
#     'état', 'remettre', 'carte', 'paix', 'noir', 'exactement', 'drôle', 'refuser', 'dès', 'président', 
#     'cours', 'grave', 'terminer', 'ciel', 'partout', 'âme', 'patron', 'amuser', 'celle', 'visage', 
#     'intéresser', 'reconnaître', 'rire', 'médecin', 'rapport', 'pardonner', 'avis', 'embrasser', 'retour', 'simple', 
#     'danser', 'exister', 'différent', 'souvent', 'lumièr', 'génial', 'libre', 'près', 'dollar', 'sûrement', 
#     'pareil', 'hôpital', 'ceci', 'réussir', 'bizarre', 'voix', 'protéger', 'honneur', 'tôt', 
#     'équipe', 'prévenir', 'cheval', 'ailleurs', 'maître', 'avion', 'bout', 'habiter', 'faim', 'ensuite', 
#     'froid', 'normal', 'déranger', 'reprendre', 'oncle', 'prix', 'retard', 'détruire', 'cadeau', 
#     'pousser', 'face', 'gueule', 'chemin', 'vivant', 'général', 'bateau', 'million', 'sac', 'impossible', 
#     'seconde', 'découvrir', 'erreur', 'soleil', 'voyage', 'sauter', 'rêver', 'détester', 'clair', 'con', 
#     'faux', 'paraître', 'balle', 'empêcher', 'maintenir', 'cheveu', 'papier', 'sujet', 'supposer', 'tranquille', 
#     'épouser', 'blanc', 'table', 'toute', 'dix', 'clé', 'agent', 'approcher', 'sens', 'craindre', 
#     'six', 'message', 'crier', 'salle', 'inviter', 'effet', 'réfléchir', 'espèce', 'arranger', 'naître', 
#     'allô', 'passé', 'bois', 'propos', 'camp', 'sorte', 'hôtel', 'début', 'souffrir', 'jambe', 
#     'remercier', 'choix', 'sécurité', 'baiser', 'avocat', 'attraper', 'client', 'courant', 'dépêcher', 'peuple', 
#     'dame', 'dessus', 'abandonner', 'vérifier', 'journal', 'sérieux', 'brûler', 'or', 'loi', 'fond', 
#     'gosse', 'fric', 'situation', 'euh', 'sauf', 'accident', 'doute', 'scène', 'soldat', 'amoureux', 
#     'assurer', 'preuve', 'humain', 'mer', 'silence', 'télé', 'victime', 'complètement', 'pute', 'calme', 
#     'derrière', 'garde', 'meurtre', 'groupe', 'crime', 'traiter', 'doucement', 'blesser', 'colonel', 'certain', 
#     'secret', 'parole', 'triste', 'rouge', 'dégager', 'soirée', 'dangereux', 'armée', 'filer', 'risquer', 
#     'dos', 'appel', 'visite', 'mener', 'fleur', 'attaquer', 'coin', 'prince', 'pire', 'bordel', 
#     'professeur', 'fumer', 'répéter', 'habitude', 'signer', 'ficher', 'mériter', 'réponse', 'rejoindre', 'discuter'

# , 
#     'village', 'pourtant', 'avancer', 'connerie', 'reposer', 'échapper', 'forme', 'bruit', 'chacun', 'diable', 
#     'exemple', 'charger', 'chat', 'ennemi', 'gamin', 'rendez-vous', 'debout', 'obliger', 'trou', 'idiot', 
#     'accompagner', 'fenêtre', 'oser', 'impression', 'intérieur', 'bouche', 'ligne', 'absolument', 'doux', 'regretter', 
#     'mur', 'enfer', 'prouver', 'boîte', 'santé', 't', 'dîner', 'couvrir', 'magnifique', 'obtenir', 
#     'cuisine', 'vue', 'terrible', 'peau', 'éviter', 'salaud', 'conseil', 'plaisanter', 'autour', 'vin', 
#     'exact', 'virer', 'supporter', 'régler', 'doigt', 'grâce', 'étrange', 'souhaiter', 'bas', 'mission', 
#     'créer', 'chanson', 'pote', 'surveiller', 'simplement', 'recommencer', 'robe', 'chaud', 'billet', 'spécial', 
#     'moyen', 'sympa', 'vaisseau', 'moi-même', 'coûter', 'surprise', 'poste', 'compris', 'anniversaire', 'signe', 
#     'vol', 'couleur', 'image', 'parier', 'est', 'arbre', 'bière', 'mme', 'poisson', 'selon', 
#     'a', 'intérêt', 'lieutenant', 'danger', 'appartenir', 'remarquer', 'animal', 'rater', 'retirer', 'bord', 
#     'tenter', 'liberté', 'règle', 'banque', 'merveilleux', 'fier', 'partager', 'classe', 'dossier', 'ressentir', 
#     'bonheur', 'défendre', 'but', 'bande', 'l', 'fatiguer', 'radio', 'prévoir', 'celui-là', 'haut', 
#     'camarade', 'douter', 'oiseau', 'vent', 'recherche', 'apprécier', 'système', 'ferme', 'capable', 'fuir', 
#     'ennui', 'tante', 'héros', 'dedans', 'excellent', 'pitié', 'appartement', 'bosser', 'respirer', 'entier', 
#     'récupérer', 'douleur', 'libérer', 'sentiment', 'grand-père', 'société', 'lancer', 'nez', 'joie', 'relation', 
#     'témoin', 'acteur', 'moitié', 'incroyable', 'bain', 'durer', 'marché', 'laver', 'dent', 'là-dedans', 
#     'mademoiselle', 'adresse', 'cousin', 'riche', 'compagnie', 'sonner', 'chaussure', 'oreille', 'grand-mère', 'ancien', 
#     'art', 'deviner', 'inutile', 'ravir', 'blague', 'avenir', 'beauté', 'laisse', 'course', 'manièr', 
#     'traverser', 'expérience', 'soin', 'hors', 'cour', 'gauche', 'stupide', 'retenir', 'liste', 'remonter', 
#     'réaliser', 'i', 'moquer', 'étudier', 'installer', 'courage', 'bleu', 'secours', 'milieu', 'proposer', 
#     'm', 'contact', 'inspecteur', 'mignon', 'projet', 'probablement', 'rôle', 'risque', 'action', 'ange', 
#     'avance', 'intéressant', 'parmi', 'langue', 'emporter', 'thé', 'laquelle', 'colère', 'départ', 'époque', 
#     'engager', 'voleur', 'cesser', 'tort', 'vacance', 'là-haut', 'machine', 'signifier', 'réparer', 'bête', 
#     'construire', 'pain', 'bar', 'chier', 'club', 'été', 'horrible', 'profiter', 'pierre', 'pleuvoir', 
#     'plusieurs', 'salope', 'tel', 'glace', 'présent', 'décision', 'juge', 'contrôle', 'séparer', 'sept', 
#     'maladie', 'quartier', 'désirer', 'travers', 'dommage', 'cigarette', 'traîner', 'respecter', 'époux', 'tas', 
#     'enfuir', 'diriger', 'crever', 'fil', 'combat', 'poursuivre', 'morceau', 'église', 'directeur', 'demande', 
#     'forcer', 'bombe', 'j', 'lequel', 'espoir', 'tueur', 'grandir', 'dimanche', 'américain', 'taxi', 
#     'interdire', 'baisser', 'enterrer', 'causer', 'cool', 'survivre', 'cinéma', 'commander', 'match', 'information', 
#     'toilette', 'note', 'gouvernement', 'monstre', 'censé', 'ennuyer', 'contraire', 'justement', 'montagne', 'prêter', 
#     'solution', 'nettoyer', 'opération', 'occasion', 'atteindre', 'rouler', 'débarrasser', 'position', 'patient', 'cerveau', 
#     'excuse', 'ridicule', 'avouer', 'vêtement', 'ben', 'regard', 'plaindre', 'remplir', 'contrôler', 'planète', 
#     'taper', 'mensonge', 'lune', 'personnel', 'démon', 'e', 'mémoire', 'magasin', 'téléphoner', 'dépendre', 
#     'vide', 'jardin', 'nature', 'trace', 'félicitation', 'parfaire', 'attaque', 'c', 'lait', 'résultat', 
#     'camion', 'neuf', 'bonne', 'étranger', 'arrivé', 'base', 'renvoyer', 'puisque', 'reine', 'repartir', 
#     'enfermer', 'parfait', 'drogue', 'droite', 'dingue', 'huit', 'pur', 'île', 'habiller', 'refaire', 
#     'couteau', 'enquête', 'goût', 'pensée', 'gêner', 'certains', 'intelligent', 'marre', 'importance', 'éteindre', 
#     'bouteille', 'champ', 'o', 'centre', 'rapporter', 'coincer', 'malheur', 'miracle', 'sacré', 'réunion', 
#     'acte', 'surprendre', 'convaincre', 'livrer', 'quels', 'pont', 'faîte', 'immédiatement', 'caméra', 'juger', 
#     'membre', 'voie', 'voisin', 'différence', 'détail', 'annoncer', 'environ', 'to', 'mille', 'haïr', 
#     'test', 'assassin', 'officier', 'proche', 'commandant', 'briser', 'gâteau', 'spectacle', 'certainement', 'enchanté', 
#     'chasser', 'attirer', 'chapeau', 'allumer', 'respect', 'd', 'sous-titrage', 'étoile', 'charmant', 'écraser']


# , 
#     'genou', 'formidable', 'arracher', 'soit', 'sorcier', 'foi', 'mien', 'sourire', 'inventer', 'zone', 
#     'honnête', 'mêler', 'énerver', 'exploser', 'réalité', 'supplier', 'étonner', 'superbe', 'méchant', 'contrat', 
#     'marche', 'déposer', 'destin', 'urgence', 'placer', 'remplacer', 'accuser', 'celle-là', 'vert', 'terrain', 
#     'nourrir', 'second', 'folie', 'presser', 'accorder', 'emmerder', 'arrière', 'reculer', 'sexe', 'élever', 
#     'nécessaire', 'piste', 'prêtre', 'usine', 'accrocher', 'appareil', 'entendu', 'fiancé', 'costume', 'déjeuner', 
#     'coller', 'code', 'danse', 'campagne', 'intention', 'anglais', 'serrer', 'valise', 'justice', 'défense', 
#     'arrêt', 'coupable', 'niveau', 'entraîner', 'bus', 'mienne', 'nerveux', 'nord', 'crise', 'connard', 
#     'moindre', 'tableau', 'piquer', 'admettre', 'restaurant', 'trésor', 'nu', 'produire', 'tombe', 'poche', 
#     'menacer', 'couple', 'gâcher', 'odeur', 'vu', 'souci', 'lorsque', 'concerner', 'énorme', 'programme', 
#     'allemand', 'toit', 'bravo', 'représenter', 'bénir', 'telle', 'rapide', 'fusil', 'enceinte', 'repas', 
#     'certaines', 'montre', 'fantôme', 'endormir', 'plage', 'entrée', 'louer', 'mine', 'hasard', 'soigner', 
#     'chasse', 'organiser', 'sortie', 'examen', 'cadavre', 'vache', 'ranger', 'passe', 'couler', 'rigoler', 
#     'commettre', 'in', 'sol', 'volonté', 'public', 'quelles', 'ventre', 'trahir', 'condition', 'débrouiller', 
#     'shérif', 'fâcher', 'parti', 'lui-même', 'samedi', 'malgré', 'étage', 'source', 'frais', 'attacher', 
#     'joindre', 'horreur', 'sexuel', 'pluie', 'responsable', 'celui-ci', 'objet', 'finalement', 'toi-même', 'presse', 
#     'siècle', 'voyager', 'larme', 'mlle', 'ombre', 'nommer', 'rat', 'cri', 'conscience', 'rechercher', 
#     'parfaitement', 'unique', 'procès', 'valeur', 'désir', 'juif', 'obéir', 'mets', 'saluer', 'direction', 
#     'présence', 'utile', 'paquet', 'sein', 'nourriture', 'mordre', 'sort', 'guérir', 'passage', 'jaloux', 
#     'nombreux', 'nul', 'sommeil', 'week-end', 'stop', 'flingue', 'article', 'adieu', 'viande', 'détendre', 
#     'interroger', 'étude', 'faillir', 'talent', 'condamner', 'cou', 'deuxième', 'au-dessus', 'espace', 'apparaître', 
#     'don', 'marquer', 'ramasser', 'militaire', 'château', 'chemise', 'mètre', 'abattre', 'unit', 'majesté', 
#     'imbécile', 'commissaire', 'taille', 'apparemment', 'connaissance', 'français', 'énergie', 'cent', 'sec', 'considérer', 
#     'pendre', 'cellule', 'combattre', 'posséder', 'discours', 'bouffer', 'effort', 'arrivée', 'observer', 'dépasser', 
#     'lycée', 'fonctionner', 'profond', 'fouiller', 'pomme', 'repos', 'goûter', 'conversation', 'insister', 'gare', 
#     'transformer', 'annuler', 'empreinte', 'oeuvre', 'réunir', 'médicament', 'blessure', 'piger', 'punir', 'renoncer', 
#     'déclarer', 'queue', 'confier', 'malin', 'théâtre', 'leçon', 'violence', 'ministre', 'rompre', 'titre', 
#     'éclater', 'alcool', 'poulet', 'péché', 'invité', 'court', 'éloigner', 'porc', 'allonger', 'front', 
#     'appuyer', 'résoudre', 'com', 'artiste', 'geste', 'os', 'université', 'chauffeur', 's', 'fabriquer', 
#     'mouvement', 'marque', 'agréable', 'autrement', 'nombre', 'balancer', 'vitesse', 'filmer', 'chaise', 'puissant', 
#     'manteau', 'ouvert', 'joyeux', 'déconner', 'saint', 'heureusement', 'naturel', 'voiler', 'naissance', 'former', 
#     'signal', 'concentrer', 'succès', 'nana', 'enfoiré', 'infirmier', 'relever', 'fruit', 'retraite', 'violer', 
#     'page', 'oeuf', 'coffre', 'neige', 'star', 'sérieusement', 'poil', 'bêtise', 'disputer', 'innocent', 
#     'lapin', 'salon', 'chaleur', 'désormais', 'sage', 'miss', 'pisser', 'contacter', 'hiver', 'collègue', 
#     'résister', 'ajouter', 'convenir', 'chaîne', 'couille', 'faible', 'celle-ci', 'réel', 'déplacer', 'bloquer', 
#     'corde', 'aveugle', 'identifier', 'minuit', 'veiller', 'politique', 'rattraper', 'planter', 'demi', 'égal', 
#     'étudiant', 'prisonnier', 'caisse', 'viser', 'génie', 'tribunal', 'malheureux', 'millier', 'lèvre', 'nulle'
# ]



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