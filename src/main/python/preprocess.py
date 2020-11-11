# encoding: utf-8
import preprocess_functions as process
import read_files as read
import os
from nltk.tokenize import sent_tokenize
from nltk.tokenize.util import regexp_span_tokenize
import numpy as np
from collections import defaultdict
from random import randint
import argparse
import configparser
import warnings
import xml.etree.cElementTree as ET


config = configparser.ConfigParser()
config.read('ident.conf')
char2int_path = config['Encoding_Vocabulary']['Char2Int']
non_operator_path = config['Label_Vocabulary']['Non_operator']
operator_path = config['Label_Vocabulary']['Operator']




def get_list_name (file_list_name):
    file_names = read.textfile2list(file_list_name)
    file_simple = [file_name.split("/")[-1] for file_name in file_names if "THYMEColonFinal" in file_name]
    read.savein_json(file_list_name.replace(".txt","_simple"),file_simple)

#get_list_name("data/dev_file.txt")
def get_train():
    file_dev = read.readfrom_json("data/dev_file_simple")
    train_all_simple = read.readfrom_json("data/train_all_simple")
    train = [train_file for train_file in train_all_simple if train_file not in file_dev]
    read.savein_json("data/train_simple",train)


def split_by_sentence(raw_text,char_vocab):
    sent_tokenize_list = sent_tokenize(raw_text)
    sent_tokenize_span_list = process.spans(sent_tokenize_list, raw_text)
    sent_span_list = list()
    max_len = list()
    for sent_tokenize_span in sent_tokenize_span_list:
        sent_spans = list(regexp_span_tokenize(sent_tokenize_span[0], r'\n'))
        for sent_span in sent_spans:
            sent_span = (sent_span[0] + sent_tokenize_span[1], sent_span[1] + sent_tokenize_span[1])
            sent = raw_text[sent_span[0]:sent_span[1]]
            for char in sent:
                char_vocab[char]+=1
            if len(sent) >= 350:
                #print sent
                multi_sent_span, multi_sent_len = process.rule_based_tokenizer(sent, sent_span)
                sent_span_list += multi_sent_span
                max_len += multi_sent_len
                if max(multi_sent_len)>350:
                    print(sent)
            elif len(list(set(sent)))>=2:
                sent_span_list.append([sent, sent_span[0], sent_span[1]])
                max_len.append(len(sent))
    return sent_span_list,max_len,char_vocab

        #read.save_in_json(raw_dir_simple[data_id] + "_sent", sent_span_list)
        #max_len.sort(reverse=True)

def xml_tag_in_sentence(sentences,posi_info_dict):
    tag_list = list()
    tag_span = posi_info_dict.keys()
    tag_span = sorted(tag_span, key=int)
    i = 0
    print('TAG_SPAN')
    print('tag_span - '.join(map(str, tag_span)))
    for sent in sentences:
        #print('Sentence - '.join(map(str, sent)))
        tag = list()
        if i < len(tag_span):
            if sent[2] < int(tag_span[i]):
                tag_list.append(tag)
            elif sent[1] <= int(tag_span[i]) and sent[2] > int(tag_span[i]):
                while True:
                    tag.append((tag_span[i],posi_info_dict[tag_span[i]]))
                    i = i + 1
                    if i < len(tag_span):
                        if int(tag_span[i]) > sent[2]:
                            tag_list.append(tag)
                            break
                    else:
                        tag_list.append(tag)
                        break
            elif sent[2] == int(tag_span[i]):
                None
        else:
            tag_list.append(tag)
        #print tag_list
    if len(sentences) != len(tag_list):
        raise Exception('The number of the sentences for tag_list and sentence_list should match.')
    print('tag_list - '.join(map(str, tag_list)))
    return tag_list

def get_idx_from_sent(padding_char,sent, word_idx_map, max_l,pad):
    """
    Transforms sentence into a list of indices. Post-Pad with zeroes.
    """
    x = []
    for i in range(pad):
        x.append(word_idx_map[padding_char])
    for word in sent:
        if word in word_idx_map.keys():
            x.append(word_idx_map[word])
        else:
            x.append(0)
    for i in range(pad):
        x.append(word_idx_map[padding_char])
    while len(x) < max_l+ 2 *pad:
        x.append(4)
    return x

def create_class_weight(n_labels, labels, mu):
    n_softmax = n_labels
    counts = np.zeros(n_softmax, dtype='int32')
    for softmax_index in labels:
        softmax_index = np.asarray(softmax_index)
        for i in range(n_softmax):
            counts[i] = counts[i] + np.count_nonzero(softmax_index == i)

    labels_dict = read.counterList2Dict(list(enumerate(counts, 0)))

    total = np.sum(list(labels_dict.values()))
    class_weight = dict()

    for key, value in labels_dict.items():
        if not value == 0:
            score = mu * total / float(value)
            class_weight[key] = score if score > 1.0 else 1.0
        else:
            class_weight[key] = 10.0

    return class_weight


def get_sample_weights_multiclass(n_labels, labels, mu1):
    class_weight = create_class_weight(n_labels, labels, mu=mu1)
    samples_weights = list()
    for instance in labels:
        sample_weights = [class_weight[category] for category in instance]
        samples_weights.append(sample_weights)
    return samples_weights


def document_level_2_sentence_level(file_dir, raw_data_path, preprocessed_path,xml_path,file_format):

    max_len_all=list()
    char_vocab = defaultdict(float)

    for data_id in range(0, len(file_dir)):
        #raw_text_path = os.path.join(raw_data_path,file_dir[data_id],file_dir[data_id])
        #preprocessed_file_path = os.path.join(preprocessed_path,file_dir[data_id],file_dir[data_id])
        raw_text_path = os.path.join(raw_data_path,file_dir[data_id])
        preprocessed_file_path = os.path.join(preprocessed_path,file_dir[data_id])

        raw_text = read.readfrom_txt(raw_text_path)
        raw_text = process.text_normalize(raw_text)
        #print('raw_text - %s' % raw_text)
        #print('raw_text AFTER NORMALIZE - %s' % raw_text)
        sent_span_list_file, max_len_file,char_vocab = split_by_sentence(raw_text,char_vocab)
        #print('sent_span_list_file - %s, max_len_file - %s,char_vocab - %s ' % (sent_span_list_file, max_len_file, char_vocab))
        max_len_all +=max_len_file
        read.savein_json(preprocessed_file_path+"_sent",sent_span_list_file)
        if xml_path != "":
            xml_file_path = os.path.join(xml_path, file_dir[data_id], file_dir[data_id] + file_format)
            #xml_file_path = os.path.join(xml_path, file_dir[data_id] + file_format)
            print('xml_file_path - %s' % xml_file_path)
            posi_info_dict = process.extract_xmltag_anafora(xml_file_path, raw_text)
            print('posi_info_dict - ')
            for key, value in posi_info_dict.items() :
                print (key, value)
            sent_tag_list_file = xml_tag_in_sentence(sent_span_list_file, posi_info_dict)
            #print('sent_tag_list_file - %s' % sent_tag_list_file)
            read.savein_json(preprocessed_file_path + "_tag", sent_tag_list_file)

    print('max_len_all - %s' % max_len_all)
    max_len_all.sort(reverse=True)
    max_len_file_name = "/".join(preprocessed_path.split('/')[:-1])+"/max_len_sent"
    read.savein_json(max_len_file_name, max_len_all)

def features_extraction(raw_data_dir,preprocessed_path,model_path,data_folder = "",mode = "train"):
    max_len = 350
    pad = 3
    input_char = list()
    char2int = read.readfrom_json(char2int_path)

    total = 0
    for data_id in range(0, len(raw_data_dir)):
        print(raw_data_dir[data_id])
        #preprocessed_file_path = os.path.join(preprocessed_path, raw_data_dir[data_id], raw_data_dir[data_id]) - TODO
        preprocessed_file_path = os.path.join(preprocessed_path, raw_data_dir[data_id])
        sent_span_list_file = read.readfrom_json(preprocessed_file_path+ "_sent")
        print(len(sent_span_list_file))

        n_sent = len(sent_span_list_file)
        for index in range(n_sent):
            total +=1
            input_char.append(get_idx_from_sent("\n",sent_span_list_file[index][0], char2int, max_len,pad))

        print("Finished processing file: ",raw_data_dir[data_id] )
    print(total)
    input_char = np.asarray(input_char, dtype="int16")

    if not os.path.exists(model_path):
        os.makedirs(model_path)
    read.save_hdf5(model_path+"/input"+data_folder, ["char"], [input_char], ['int16'])

def output_encoding(raw_data_dir,preprocessed_path,model_path,data_folder="",activation="softmax",type="interval"):   ###type in "[interval","operator","explicit_operator","implicit_operator"]
    target_labels = defaultdict(float)
    if type not in ["interval","operator","explicit_operator","implicit_operator"]:
        return
    interval = read.textfile2list(non_operator_path)
    operator = read.textfile2list(operator_path)
    max_len = 350
    n_marks = 3
    max_len_text = max_len+2*n_marks
    n_output = 0
    final_labels = 0

    if activation == "sigmoid":
        final_labels = interval+operator
        n_output = len(final_labels)
    elif activation =="softmax":
        if "interval" in type:
            final_labels = interval
        elif "operator" in type:
            final_labels  = operator
        n_output = len(final_labels) +1

    one_hot = read.counterList2Dict(list(enumerate(final_labels, 1)))
    output_one_hot = {y:x for x,y in one_hot.items()}

    sample_weights_output = []
    outputs = []
    total_with_timex =0
    n_sent_total = 0
    for data_id in range(0, len(raw_data_dir)):
        #preprocessed_file_path = os.path.join(preprocessed_path, raw_data_dir[data_id], raw_data_dir[data_id]) - TODO
        preprocessed_file_path = os.path.join(preprocessed_path, raw_data_dir[data_id])
        sent_span_list_file = read.readfrom_json(preprocessed_file_path+ "_sent")
        tag_span_list_file = read.readfrom_json(preprocessed_file_path + "_tag")
        n_sent = len(tag_span_list_file)
        n_sent_total +=n_sent
        for index in range(n_sent):
            sent_info = sent_span_list_file[index]
            tag_info = tag_span_list_file[index]

            sentence_start = sent_info[1]
            label_encoding_sent = np.zeros((max_len_text, n_output))
            if activation == "softmax":
                label_encoding_sent[:, 0] = 1
            sample_weights_sent = np.zeros(max_len_text)

            for label in tag_info:
                posi, info = label
                position = int(posi) - sentence_start
                posi_end = int(info[0]) -sentence_start
                info_new = list(set(info[2:]))

                if activation == "sigmoid":

                    label_indices = [output_one_hot[token_tag] for token_tag in info_new if token_tag in output_one_hot]
                    k = np.sum(np.eye(n_output)[[sigmoid_index - 1 for sigmoid_index in label_indices]], axis=0)

                    label_encoding_sent[position + n_marks:posi_end + n_marks, :] = np.repeat([k], posi_end - position,axis=0)


                elif activation == "softmax":
                    if "explicit" in type or "interval" in type:
                        target_label = process.get_explict_label(info_new, interval, operator)
                    elif "implicit" in type.split("_"):
                        target_label = process.get_implict_label(info_new, interval, operator)
                    for token_tag in target_label:
                        if token_tag in final_labels:
                            target_labels[token_tag]+=1.0

                    label_indices = [output_one_hot[token_tag] for token_tag in target_label if token_tag in final_labels]
                    if len(label_indices) != 0:
                        k = np.sum(np.eye(n_output)[[softmax_index for softmax_index in label_indices]], axis=0)
                        label_encoding_sent[position + n_marks:posi_end + n_marks, :] = np.repeat([k], posi_end - position,axis=0)
                t = len(label_indices)
                if t>=1:
                    sample_weights_sent[position + n_marks:posi_end + n_marks] = label_indices[randint(0, t - 1)]
            sample_weights_output.append(sample_weights_sent)
            outputs.append(label_encoding_sent)
            total_with_timex += 1
            #print total_with_timex
    print(n_sent_total)
    sample_weights = np.asarray(sample_weights_output)
    sample_weights = get_sample_weights_multiclass(n_output, sample_weights, 0.05)
    #print target_labels
    np.save(model_path+"/sample_weights" +data_folder+ "_"+type+"_"+activation, sample_weights)
    read.save_hdf5(model_path +"/output" + data_folder + "_"+type+"_"+activation,[type+"_"+activation] , [outputs], ['int8'])

def main(file_dir,preprocessed_path,model_path,encode_output = True,split_output = True):
    file_n = len(file_dir)
    # if 25<file_n<=40:
    folder_n = np.int(np.round(np.divide(float(file_n),20.00)))
    folder = list(map(lambda x: int(x), np.linspace(0, file_n, folder_n + 1)))
    #################### for the amount of documents ranges from 40 -.. ########################
    # else:
    # folder_n = np.int(np.divide(file_n,20))
    # folder = list(map(lambda x: int(x), np.linspace(0, file_n, folder_n + 1)))

    if split_output == True:
        for version in range(folder_n):
            start = folder[version]
            end = folder[version + 1]
            raw_data_dir_sub = file_dir[start:end]
            features_extraction(raw_data_dir_sub, preprocessed_path,model_path, data_folder=str(version),mode = mode)
            if encode_output == True:
                output_encoding(raw_data_dir_sub,preprocessed_path,model_path,data_folder = str(version),activation="softmax",type="interval")
                output_encoding(raw_data_dir_sub, preprocessed_path,model_path, data_folder=str(version), activation="softmax",type="explicit_operator")
                output_encoding(raw_data_dir_sub, preprocessed_path,model_path, data_folder=str(version),activation="softmax",type="implicit_operator")


    else:
        start = 0
        end = file_n
        raw_data_dir_sub = file_dir[start:end]
        features_extraction(raw_data_dir_sub, preprocessed_path,model_path,mode = mode)
        if encode_output == True :
            output_encoding(raw_data_dir_sub, preprocessed_path,model_path,activation="softmax",type="interval")
            output_encoding(raw_data_dir_sub, preprocessed_path,model_path, activation="softmax",type="explicit_operator")
            output_encoding(raw_data_dir_sub, preprocessed_path,model_path,activation="softmax",type="implicit_operator")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process features and output encoding for time identification task.')

    parser.add_argument('-raw',
                        help='the direcotory of raw texts',default="")

    parser.add_argument('-xml',
                        help='the direcotory of annotation files',default="")

    parser.add_argument('-processed_output',
                        help='output path for all preprocessed files',required=True)

    parser.add_argument('-model_output',
                        help='output path for all preprocessed files',required=True)

    parser.add_argument('-format',
                        help='the format of annotation file',default=".TimeML.gold.completed.xml")

    parser.add_argument('-processed',
                        help='whether to process raw texts',default="true")

    parser.add_argument('--mode',
                        help='Whether to split the raw files into different fractions in order to fit the memory',default="no-split")

    args = parser.parse_args()
    raw_data_path = args.raw
    xml_path = args.xml
    preprocessed_path = args.processed_output
    model_path = args.model_output

    output_format = args.format
    documents_preprocessed = args.processed
    mode = args.mode

# raw_data_path = "data/TempEval-2013/Test"
#
# xml_path ="data/TempEval-2013/Test"
# preprocessed_path = "data/Processed_TempEval/Test_new"
# model_path = "data/Processed_TempEval/new11/"
# documents_preprocessed = "no"
# mode = "no"
# output_format = ".TimeNorm.gold.completed.xml"

    file_dir = []
    print("raw_data_path "+ raw_data_path)
    for doc in os.listdir(raw_data_path):
        if not doc.endswith(".txt") and not doc.endswith(".npy") and not doc.endswith(".xml") and not doc.endswith(".dct") and not doc.startswith('.'):
            file_dir.append(doc)

    split_output = False
    encode_output = False
    preprocessed = False

    if xml_path !="":
        encode_output = True

    if mode =="split":
        split_output = True

    if documents_preprocessed == "true":
        preprocessed = True

    if preprocessed == True:
        print('[%s]' % ', '.join(map(str, file_dir)) + " : " + preprocessed_path + " : " + model_path + " : " + xml_path)
        document_level_2_sentence_level(file_dir, raw_data_path, preprocessed_path,xml_path,file_format = output_format )


    print('PROCESSING MAIN....')
    print('[%s]' % ', '.join(map(str, file_dir)) + " : " + preprocessed_path + " : " + model_path)  
    main(file_dir, preprocessed_path,model_path,encode_output = encode_output,split_output = split_output)







