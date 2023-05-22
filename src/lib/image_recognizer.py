from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer
import torch
from PIL import Image


class ImageCaptionMaker:

    def __init__(self):
        self.__model = VisionEncoderDecoderModel.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
        self.__feature_extractor = ViTImageProcessor.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
        self.__tokenizer = AutoTokenizer.from_pretrained("nlpconnect/vit-gpt2-image-captioning")
        self.__device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.__model.to(self.__device)
        self.__max_length = 16
        self.__num_beams = 4
        self.__gen_kwargs = {"max_length": self.__max_length, "num_beams": self.__num_beams}

    def caption(self, image):
        if image.mode != "RGB":
            image = image.convert(mode="RGB")

        images = [image]
        pixel_values = self.__feature_extractor(images=images, return_tensors="pt").pixel_values
        pixel_values = pixel_values.to(self.__device)
        output_ids = self.__model.generate(pixel_values, **self.__gen_kwargs)
        preds = self.__tokenizer.batch_decode(output_ids, skip_special_tokens=True)
        preds = [pred.strip() for pred in preds]
        return preds[0]