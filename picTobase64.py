import base64
import numpy as np
import cv2
from PIL import Image
from io import BytesIO
import time


# cv2转base64
# def cv2_to_base64(img):
#     img = cv2.imencode('.jpg', img)[1]
#     image_code = str(base64.b64encode(img))[2:-1]
#
#     return image_code
#
#
# # base64转cv2
# def base64_to_cv2(base64_code):
#     img_data = base64.b64decode(base64_code)
#     img_array = np.frombuffer(img_data, np.uint8)
#     img = cv2.imdecode(img_array, cv2.COLOR_RGB2BGR)
#
#     return img
#
#
# # base64转PIL
# def base64_to_pil(base64_str):
#     image = base64.b64decode(base64_str)
#     image = BytesIO(image)
#     image = Image.open(image)
#
#     return image
#
#
# # PIL转base64
# def pil_to_base64(image):
#     img = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
#     base64_str = cv2_to_base64(img)
#
#     return base64_str
#
#
# # PIL转cv2
# def pil_to_cv2(image):
#     img = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
#
#     return img
#
#
# # cv2转PIL
# def cv2_to_pil(img):
#     image = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
#
#     return image
#
#
# pi = open('pic/8x8/1.png', 'rb')
# ba = base64.b64encode(pi.read())
# print(ba)
# pi.close()
#
# img = base64_to_cv2(
#     "iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAYAAADED76LAAAAWUlEQVQYlWNkYGT4H+TqwoANrNu9h4ExyM3lP1ZZKGCBMdZOzUCRCM6eAaaZYAKMqiFwSRT2/9triLMCZiS6lXArwK7etQeMkQEToxrCvv+314Ax3H61EAYAKLcasCJ/EIQAAAAASUVORK5CYII=")
# print(img)


class PicAndBase64:
    def __init__(self, code):
        self.base64_code = code
        self.img = None
        self._base64_to_cv2()

    def _base64_to_cv2(self):
        img_data = base64.b64decode(self.base64_code)
        img_array = np.frombuffer(img_data, np.uint8)
        self.img = cv2.imdecode(img_array, cv2.COLOR_BGR2RGB)

    def _rgb_to_bytes(self, b, g, r) -> bytes:
        return (((r & 0xf8) << 8) | ((g & 0xfc) << 3) | (b >> 3)).to_bytes(2, byteorder="big", signed=False)

    def getBase64Pixel(self) -> bytes:
        value = bytes([self.img.shape[0], self.img.shape[1]])
        for i in self.img:
            for j in i:
                value += self._rgb_to_bytes(int(j[0]), int(j[1]), int(j[2]))
        return value
