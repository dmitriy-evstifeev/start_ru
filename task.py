# -*- coding: utf-8 -*-
from mongoengine import *
import enum
import random
import unittest


class ImagesEnum(enum.Enum):
    cover = 'cover'
    background = 'background'
    foreground = 'foreground'


class QualityEnum(enum.IntEnum):
    LD = 0
    SD = 1
    HD = 2
    FULL_HD = 3


class File(EmbeddedDocument):
    path = StringField()
    quality = IntField()


class Quote(EmbeddedDocument):
    source = StringField()
    text = StringField()


class Episode(EmbeddedDocument):
    num = IntField()
    alias = StringField()
    files = EmbeddedDocumentListField('File')


class Season(Document):
    num = IntField()
    alias = StringField()
    episodes = EmbeddedDocumentListField('Episode', db_field='items')
    meta = {
        'collection': 'products',
        'allow_inheritance': True
    }


class Series(Document):
    title = StringField()
    alias = StringField()
    description = StringField()
    seasons = ListField(ReferenceField('Season'), db_field='items')
    quote = EmbeddedDocumentField('Quote')
    images = MapField(URLField())
    meta = {
        'collection': 'products',
        'allow_inheritance': True
    }


class TestTask(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        connect('test', host='mongo')

    def test_01_create_documents(self):
        def __quote(i):
            source = 'QuoteSource %i' % i
            return {'source': source, 'text': 'test quote'}

        def __images(i):
            return {img.value: 'image path %i' % i for img in ImagesEnum}

        def __files():
            files = list()
            for i in QualityEnum:
                f = File(quality=i, path='file path %i' % i)
                files.append(f)
            return files

        def __episodes():
            episodes = list()
            for i in range(0, random.randint(1, 30)):
                s = Episode(num=i, alias='episode%i' % i, files=__files())
                episodes.append(s)
            return episodes

        def __seasons():
            seasons = list()
            for i in range(0, random.randint(1, 10)):
                s = Season(num=i, alias='season%i' % i, episodes=__episodes())
                s.save()
                seasons.append(s)
            return seasons

        def __series():
            series = list()
            for i in range(0, random.randint(1, 10)):
                s = Series.objects(
                    title='series %i' % i,
                    alias='series%i' % i
                    ).modify(
                        upsert=True,
                        new=True,
                        set__quote=__quote(i),
                        set__images=__images(i),
                        set__description='description %i' % i,
                        set__seasons=__seasons())
                series.append(s)
            return series
        self.assertTrue(__series())

    def test_02_create_documents(self):
        """
            ???????????????? ???????????? ?????????????? ???????????? ?????????? ???????????????????? ??????????????:
            [
              {
                "path": "/series/<alias ??????????????>",
                "title": "<title ??????????????>",
                "description": "<description ??????????????>",
                "cover": "<?????????????????????? ???? ???????? images ?? ???????????? ImagesEnum.cover>",
                "quote": "<???????????????? quote.text>",
                "quote_source": "<???????????????? quote.source>",
                "slide": {
                  "background": "<?????????????????????? ???? ???????? images ?? ???????????? ImagesEnum.background>",
                  "foreground": "<?????????????????????? ???? ???????? images ?? ???????????? ImagesEnum.foreground>"
                }
                "seasons": [
                  {
                    "path": "/series/<alias ??????????????>/<alias ????????????>",
                    "title": "<num ????????????> ??????????",
                    "episodes": [
                      {
                        "path": "/series/<alias ??????????????>/<alias ????????????>/<alias ??????????????>",
                        "title": "???????????? <num ????????????>",
                        "files": [
                          {
                            "path": "<path ??????????>",
                            "label": "<???????????????? enum ???????? QualityEnum>",
                            "quality": "<???????????????? enum ???????? QualityEnum>"
                          }
                        ]
                      }
                    ]
                  }
                ]
              }
            ]
        """
        
        db.products.aggregate([
          {
            $match: {
              _cls: "Series"
            }
          },
          {
            $lookup: {
              from: "products",
              localField: "items",
              foreignField: "_id",
              as: "seasons"
            }
          },
          {
            $project: {
              _id: 0,
              path: {
                $concat: [
                  "/series/",
                  "$alias"
                ]
              },
              title: 1,
              description: 1,
              cover: "$images.cover",
              quote: "$quote.text",
              quote_source: "$quote.source",
              slide: {
                background: "$images.background",
                foreground: "$images.foreground"
              },
              seasons: {
                $map: {
                  input: "$seasons",
                  as: "season",
                  in: {
                    path: {
                      $concat: [
                        "/series/",
                        "$alias",
                        "/",
                        "$$season.alias"
                      ]
                    },
                    title: {
                      $concat: [
                        {
                          "$toString": "$$season.num"
                        },
                        " ??????????"
                      ]
                    },
                    episodes: {
                      $map: {
                        input: "$$season.items",
                        as: "episode",
                        in: {
                          path: {
                            $concat: [
                              "/series/",
                              "$alias",
                              "/",
                              "$$season.alias",
                              "/",
                              "$$episode.alias"
                            ]
                          },
                          title: {
                            $concat: [
                              "???????????? ",
                              {
                                "$toString": "$$episode.num"
                              }
                            ]
                          },
                          files: {
                            $map: {
                              input: "$$episode.files",
                              as: "file",
                              in: {
                                path: "$$file.path",
                                label: {
                                  $switch: {
                                    branches: [
                                      {
                                        case: {
                                          "$eq": [
                                            "$$file.quality",
                                            0
                                          ]
                                        },
                                        then: "LD"
                                      },
                                      {
                                        case: {
                                          "$eq": [
                                            "$$file.quality",
                                            1
                                          ]
                                        },
                                        then: "SD"
                                      },
                                      {
                                        case: {
                                          "$eq": [
                                            "$$file.quality",
                                            2
                                          ]
                                        },
                                        then: "HD"
                                      },
                                      {
                                        case: {
                                          "$eq": [
                                            "$$file.quality",
                                            3
                                          ]
                                        },
                                        then: "FULL_HD"
                                      }
                                    ]
                                  }
                                },
                                quality: "$$file.quality"
                              }
                            }
                          }
                        }
                      }
                    }
                  }
                }
              },
            }
          }
        ])

if __name__ == '__main__':
    unittest.main()
