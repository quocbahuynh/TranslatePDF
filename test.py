import argostranslate.translate

text = "Hello world"
translated = argostranslate.translate.translate(text, "en", "vi")

print(translated)