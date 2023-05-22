from .translator_to_en import translate_query
from .image_recognizer import ImageCaptionMaker
from sentence_transformers import SentenceTransformer, util


class ImageHandler:

    def __init__(self):
        self.__images = {}
        self.__inv_images = {}
        self.__caption_maker = ImageCaptionMaker()
        self.__model = SentenceTransformer('all-MiniLM-L6-v2')

    def process_image(self, image, id, api_image):
        if (id, api_image) in self.__images:
            return
        caption = self.__caption_maker.caption(image)
        self.__images[(id, api_image)] = caption
        if caption in self.__inv_images:
            if isinstance(self.__inv_images[caption], list):
                self.__inv_images[caption].append((id, api_image))
            else:
                self.__inv_images[caption] = [self.__inv_images[caption], (id, api_image)]
        else:
            self.__inv_images[caption] = (id, api_image)

    def get_images(self, query, count):
        if len(self.__images) == 0:
            return []
        ratio = self.__compare_image(translate_query(query))
        images = []
        for (caption, _) in ratio:
            if count <= 0:
                break

            selected_images = self.__inv_images[caption]
            if isinstance(selected_images, list):
                count_chosen_images = min(count, len(selected_images))
                for i in range(count_chosen_images):
                    images.append(selected_images[i])
                count -= count_chosen_images
            else:
                images.append(selected_images)
                count -= 1

        return images

    def __compare_image(self, query):
        captions = list(set(self.__images.values()))
        query_embedding = self.__model.encode(query)
        passage_embedding = self.__model.encode(captions)
        score = util.dot_score(query_embedding, passage_embedding).numpy()[0]
        ratio = list(zip(captions, score))
        ratio.sort(key=lambda x: x[1], reverse=True)
        return ratio

    def is_same_id(self, id):
        return id in self.__images