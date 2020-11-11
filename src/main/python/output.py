import read_files as read
import os
import process_functions as output
import numpy as np
from keras.models import load_model
import argparse
import configparser

config = configparser.ConfigParser()
config.read('ident.conf')
non_operator_path = config['Label_Vocabulary']['Non_operator']
operator_path = config['Label_Vocabulary']['Operator']

def span2xmlfiles(data_spans,file_name_simple):
    import anafora
    data = anafora.AnaforaData()
    id = 0
    for data_span in data_spans:
        e = anafora.AnaforaEntity()
        e.spans = ((int(data_span[0]), int(data_span[1])+1),)
        e.type = data_span[2]
        e.id = str(id)+"@e@" + file_name_simple
        data.annotations.append(e)
        id+=1
    data.indent()
    return data

def sentence_length(texts):
   sent_len = []
   for text in texts:
      for i in range(1,356):
        if text[-i] !=4:
           sent_len.append(357-i)
           break
   return sent_len

def generate_output_multiclass(sent_len,model,input,doc_list_sub, processed_path,output_pred_path,pred =True,data_folder = "",format_abbre = ".TimeNorm.system.completed.xml"):
    non_operator = read.textfile2list(non_operator_path)
    print('non_operator')
    print(non_operator)
    operator = read.textfile2list(operator_path)
    print('operator')
    print(operator)
    labels_index = [non_operator,operator,operator]
    print('labels_index')
    print(labels_index)
    classes, probs = output.make_prediction_function_multiclass(input, model, output_pred_path)
    print('sent_len')
    print(sent_len)
    print('classes, probs - ')
    print(classes)
    #print(probs)
    if pred == True:
        np.save(output_pred_path + "/y_predict_classes"+data_folder, classes)
        read.savein_pickle(output_pred_path + "/y_predict_proba"+data_folder, probs)

    spans = list()
    int2labels = list()
    for index in range(len(classes)):
        class_loc = output.found_location_with_constraint(classes[index], sent_len)
        print('class_loc')
        print(class_loc)
        span = output.loc2span(class_loc, probs[index],post_process = False)
        print('span')
        print(span)
        spans.append(span)

        one_hot = read.counterList2Dict(list(enumerate(labels_index[index], 1)))
        one_hot = {y: x for x, y in one_hot.items()}
        int2label = dict((int, char) for char, int in one_hot.items())
        int2labels.append(int2label)

    n_marks =3
    sent_index = 0

    for data_id in range(0,len(doc_list_sub)):
        print('HERE %s', doc_list_sub[data_id])
        print(os.path.join(processed_path,doc_list_sub[data_id]+"_sent"))
        sent_spans = read.readfrom_json(os.path.join(processed_path,doc_list_sub[data_id]+"_sent"))
        print('sent_spans %s', sent_spans)
        data_span = list()
        for sent_span in sent_spans:
            """ print('sent_span - ')
            print(sent_span)
            posi_start = sent_span[1]
            posi_end = sent_span[2]
            label = sent_span[0]
            print('posi_start:%s posi_end:%s, label:%s', (posi_start,posi_end,label))
            data_span.append([posi_start-n_marks+sent_span[1],posi_end-n_marks+ sent_span[1],int2labels[index][label]]) """
            print('classes - ', range(len(classes)))
            for index in range(len(classes)):
                #print('index - ' + index + ':' + sent_index)
                """ print(index)
                print(sent_index) """
                span_list = spans[index][sent_index]
                #print('span_list - ')
                #print(len(span_list[0]))
                #print(span_list)
                if len(span_list[0]) <1:
                    pass
                else:
                    for [posi_start,posi_end,label] in span_list:
                        print('posi_start:%s posi_end:%s, label:%s', (posi_start,posi_end,label))
                        data_span.append([posi_start-n_marks+sent_span[1],posi_end-n_marks+ sent_span[1],int2labels[index][label]])
            sent_index += 1
        print('data_span - ', data_span)
        data = span2xmlfiles(data_span,doc_list_sub[data_id])
        print('data %s', data)
        output_path = os.path.join(output_pred_path,doc_list_sub[data_id],doc_list_sub[data_id])
        read.create_folder(output_path)
        data.to_file(output_path+format_abbre)
    del classes,probs,input


def main(model_path,input_path,doc_list,raw_data_path, preocessed_path, output_pred_path,output_format,pred=True, portion = 0,split_output = False):
    file_n = len(doc_list)
    #################### for the amount of documents ranges from 20-40 #########################
    folder_n = int(np.round(np.divide(float(file_n),20.00)))
    folder = list(map(lambda x: int(x), np.linspace(0, file_n, folder_n + 1)))
    #################### for the amount of documents ranges from 40 -.. ########################
    # folder_n = np.divide(file_n,20)
    # folder = list(map(lambda x: int(x), np.linspace(0, file_n, folder_n + 1)))

    model = load_model(model_path)
    if split_output ==True :
        k=portion
        for version in range(k,k+1):
            start = folder[version]
            end = folder[version + 1]
            doc_list_sub = doc_list[start:end]
            input = read.load_hdf5(input_path + "/input" + str(version), ["char"])[0]
            sent_len = sentence_length(input)
            generate_output_multiclass(sent_len, model, input, doc_list_sub, preocessed_path,output_pred_path,pred=pred,data_folder = str(version),format_abbre =output_format)
    else:
        start = 0
        end = file_n
        doc_list_sub = doc_list[start:end]
        print('INPUT PATH - ', input_path+"/input", ["char"])
        input = read.load_hdf5(input_path+"/input", ["char"])[0]
        print('INPUT - ', input)
        sent_len = sentence_length(input)
        generate_output_multiclass(sent_len, model, input,doc_list_sub,preocessed_path, output_pred_path,pred=pred,data_folder = "",format_abbre =output_format)

    #if evaluate=="true":
    output.evaluate(preocessed_path,output_pred_path,raw_data_path,doc_list,output_format)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate the SCATE annofora annotation for the documents.')
    parser.add_argument('-raw',
                        help='raw data path',required=True)
    parser.add_argument('-model',
                        help='specify the model path',default="")
    parser.add_argument('-processed_path',
                        help='specify the preprocessed path',default="")

    parser.add_argument('-input',
                        help='the path of the model input files',default="")

    parser.add_argument('-out',
                        help='output path for all preprocessed files',required=True)

    parser.add_argument('-format',
                        help='output path for all preprocessed files',default=".TimeML.gold.completed.xml")

    parser.add_argument('-mode',
                        help='Whether requried to save the output probability',default="false")

    parser.add_argument('-portion',
                        help='using portion of the data',default=0)

    parser.add_argument('-split',
                        help='Whether to split the raw files into different fractions in order to fit the memory',default="false")

    args = parser.parse_args()
    raw_data_path = args.raw
    preprocessed_path = args.processed_path
    input_path = args.input
    model_path = args.model
    output_pred_path = args.out
    output_format = args.format
    mode = args.mode
    portion = int(args.portion)
    split_the_output = args.split

    pred = True
    split = False

    if mode =="false":
        pred = False

    if split_the_output =="true":
        split =True


    doc_list = []
    for doc in os.listdir(raw_data_path):
        if not doc.endswith(".txt") and not doc.endswith(".npy") and not doc.endswith(".xml") and not doc.endswith(".dct"):
            doc_list.append(doc)



    main(model_path, input_path, doc_list, raw_data_path, preprocessed_path, output_pred_path, output_format,split_output=split,portion=portion, pred=pred)
