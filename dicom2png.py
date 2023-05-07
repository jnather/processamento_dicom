# -*- coding: utf-8 -*-
"""
DICOM to PNG Converter

Autor: Julio Cesar Nather Junior

Este script converte arquivos DICOM para imagens PNG em escala de cinza, aplicando janelamento, normalização e redimensionamento.
Utiliza múltiplas threads para processar os arquivos em paralelo, melhorando a performance.

Dependências:
- pydicom
- numpy
- Pillow
- opencv-python

Instruções:
1. Coloque os arquivos DICOM na pasta de sua escolha.
2. Execute este script, passando o caminho da pasta como argumento, por exemplo: python script.py baixados.
3. As imagens processadas serão salvas na pasta com o mesmo nome da original acrescido de "_png", por exemplo: "baixados_png".
"""


# Importa as bibliotecas necessárias
import pydicom
import os

import numpy as np

from PIL import Image
import cv2

import pickle
import random,string

from threading import Thread

import threading

import math


# Definir funções auxiliares

def get_first_of_dicom_field_as_int(x):
    if type(x) == pydicom.multival.MultiValue:
        return int(x[0])
    return int(x)

def get_metadata_from_dicom(img_dicom):
    metadata = {
        "window_center": img_dicom.WindowCenter,
        "window_width": img_dicom.WindowWidth,
        "intercept": img_dicom.RescaleIntercept if "RescaleIntercept" in img_dicom else 0.0,
        "slope": img_dicom.RescaleSlope if "RescaleSlope" in img_dicom else 0.0,
    }
    return {k: get_first_of_dicom_field_as_int(v) for k, v in metadata.items()}

def window_image(img, window_center, window_width, intercept, slope):
    img = img * slope + intercept
    img_min = window_center - window_width // 2
    img_max = window_center + window_width // 2
    img[img < img_min] = img_min
    img[img > img_max] = img_max
    return img

def normalize_minmax(img):
    # Encontrar o valor mínimo e máximo da imagem
    mi, ma = img.min(), img.max()
    
    # Normalizar a imagem para o intervalo [0, 1]
    return (img - mi) / (ma - mi)

def resize_img_cv2(im,desired_size):
    # Definir o tamanho desejado para a imagem
    #desired_size = 224
    
    # Obter as dimensões da imagem
    old_size = im.shape[:2] # old_size está no formato (altura, largura)

    # Calcular a proporção para redimensionar a imagem
    ratio = float(desired_size)/max(old_size)
    new_size = tuple([int(x*ratio) for x in old_size])

    # Redimensionar a imagem
    im = cv2.resize(im, (new_size[1], new_size[0]))

    # Calcular a quantidade de preenchimento necessário para alcançar o tamanho desejado
    delta_w = desired_size - new_size[1]
    delta_h = desired_size - new_size[0]
    top, bottom = delta_h//2, delta_h-(delta_h//2)
    left, right = delta_w//2, delta_w-(delta_w//2)

    # Definir a cor do preenchimento
    color = [0, 0, 0]
    
    # Adicionar o preenchimento à imagem
    new_im = cv2.copyMakeBorder(im, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)

    return new_im

# Definir a função process_file
def process_file(nome_imagem_dcm, caminhoArquivo, caminhoPastaOutput):

    # Verificar se a imagem já foi processada
    if not os.path.exists(os.path.join(caminhoPastaOutput,str(nome_imagem_dcm)+".png")):              

        try:
            # Ler o arquivo DICOM
            ds = pydicom.dcmread(caminhoArquivo, force=True)

            # Obter os metadados do arquivo DICOM
            metadata = get_metadata_from_dicom(ds)

            # Aplicar janelamento e normalização na imagem
            pixel_array = window_image(ds.pixel_array, **metadata)
            pixel_array = normalize_minmax(pixel_array) * 255

            # Inverter a imagem se for MONOCHROME1
            if ds.PhotometricInterpretation == "MONOCHROME1":
                pixel_array_max = np.amax(pixel_array) 
                pixel_array_min = np.amin(pixel_array) 
                pixel_range = pixel_array_max - pixel_array_min          
                with np.nditer(pixel_array, op_flags=['readwrite']) as it:
                    for x in it:
                        x[...] = pixel_range - x
            else:
                pass

            # Verificar se a imagem não contém valores NaN
            if not math.isnan(pixel_array.min()):

                # Redimensionar a imagem
                pixel_array = resize_img_cv2(pixel_array,384)

                # Converter o array em um objeto Image
                im = Image.fromarray(pixel_array)

                # Converter a imagem para escala de cinza
                im = im.convert("L")

                # Salvar a imagem em formato PNG
                im.save(os.path.join(caminhoPastaOutput,str(ds.SOPInstanceUID)+".png"), "PNG")
        except Exception as e:
            print("Erro: ", e)

    return 0

def find_dcm_files_recursively(folder_path):
    file_dict = {}
    count = 0

    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(".dcm"):
                file_path = os.path.join(root, file)
                file_key = f"img_{count}"
                file_dict[file_key] = file_path
                count += 1
            
    return file_dict

def processarPastas(caminhoPasta):  

    # Definir os caminhos das pastas de entrada e saída
    #caminhoPasta = "baixados"
    caminhoPastaOutput = caminhoPasta + "_png" #caminhoPastaOutput = "baixados_png" 

    # Verificar se a pasta de saída existe, caso contrário, criar
    if not os.path.exists(caminhoPastaOutput):         
        os.makedirs(caminhoPastaOutput)    
    
    dcm_file_dict = find_dcm_files_recursively(caminhoPasta)
    #print(dcm_file_dict)

    # Iniciar as threads de processamento
    threads = []
    for nome_imagem_dcm in dcm_file_dict:#next(os.walk(caminhoPasta))[2]:
        if os.path.exists(os.path.join(caminhoPastaOutput,str(nome_imagem_dcm)+".png")):
            continue

        # Criar uma thread para processar cada arquivo
        t = Thread(target=process_file, args=(nome_imagem_dcm, dcm_file_dict[nome_imagem_dcm], caminhoPastaOutput))
        threads.append(t)
        t.start()

    # Aguardar o término de todas as threads
    for t in threads:

        t.join()


if __name__ == "__main__":
    import sys
    processarPastas(sys.argv[1])