from googletrans import Translator

translator = Translator()


def translate_query(query):
    return translator.translate(query, dest='en').text