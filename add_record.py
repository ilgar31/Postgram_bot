import mysql.connector
from mysql.connector import Error
import json
import datetime
import aiomysql
import os
import urllib.parse
import re
import asyncio
import random
import uuid
from slugify import slugify
import asyncssh
import paramiko


async def clean_search_string(input_string):
    # Оставляем только буквы, цифры и пробелы
    cleaned_string = re.sub(r'[^a-zA-Z0-9\s]', '', input_string)
    return cleaned_string


async def get_user_id_and_community_id(username, communityname, host='---', database='---',
                                 user='---', password='---'):
    try:
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)

            sql1 = "SELECT id FROM users WHERE username = %s"
            cursor.execute(sql1, (username,))
            result1 = cursor.fetchone()

            sql2 = "SELECT id FROM communities WHERE slug = %s"
            cursor.execute(sql2, (communityname,))
            result2 = cursor.fetchone()

            if result1 and result2:
                return str(result1['id']), str(result2['id'])
            else:
                print("Пользователь не найден.")
                return None

    except Error as e:
        print(f"Ошибка при подключении к MySQL: {e}")
        return None

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("Соединение с MySQL закрыто.")


async def get_tag(tag, host='---', database='---', user='---', password='---'):
    try:
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )

        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)

            sql1 = "SELECT tag_id FROM tags WHERE name = %s"
            cursor.execute(sql1, (tag,))
            result1 = cursor.fetchone()

            sql2 = "SELECT tag_id FROM tags WHERE normalized = %s"
            cursor.execute(sql2, (await clean_search_string(slugify(tag)), ))
            result2 = cursor.fetchone()

            if result1:
                return str(result1['tag_id'])
            elif result2:
                return -1
            else:
                return 0

    except Error as e:
        print(f"Ошибка при подключении к MySQL: {e}")
        return None

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("Соединение с MySQL закрыто.")


async def upload_file_to_server(images_list, hostname, port, username, password):
    try:
        transport = paramiko.Transport((hostname, port))
        transport.connect(username=username, password=password)

        sftp = paramiko.SFTPClient.from_transport(transport)

        for local_path, remote_path in images_list:
            remote_dir = os.path.dirname(remote_path)
            try:
                sftp.listdir(remote_dir)
            except IOError:
                print(f"Директория {remote_dir} не существует на сервере. Создание директории.")
                sftp.mkdir(remote_dir)

            sftp.put(local_path, remote_path)
            print(f"Файл {local_path} успешно загружен на {remote_path}")

        sftp.close()
        transport.close()
    except Exception as e:
        print(f"Ошибка при загрузке файла на сервер: {e}")


async def insert_record(data, media_data, tags, image_path, extra_media, extra_media_paths, host='---', database='---',
                                 user='---', password='---'):
    try:
        # Подключаемся к базе данных
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )

        if connection.is_connected():
            cursor = connection.cursor()

            # Формируем SQL-запрос для вставки данных
            placeholders = ', '.join(['%s'] * len(data))
            columns = ', '.join(data.keys())
            sql = f"INSERT INTO stories ({columns}) VALUES ({placeholders})"
            # Выполняем запрос
            cursor.execute(sql, tuple(data.values()))

            story_id = cursor.lastrowid

            connection.commit()
            print("Запись успешно добавлена в таблицу stories.")

            if media_data:
                media_data['model_id'] = story_id

                placeholders = ', '.join(['%s'] * len(media_data))
                columns = ', '.join(media_data.keys())
                sql = f"INSERT INTO media ({columns}) VALUES ({placeholders})"
                cursor.execute(sql, tuple(media_data.values()))

                images_list = []
                images_list.append([image_path, f'domains/postgram.ru/html/storage/app/uploads/stories/img/{media_data["file_name"]}'])
                images_list.append([image_path, f'domains/postgram.ru/html/storage/app/uploads/stories/{cursor.lastrowid}/{media_data["file_name"]}'])
                if extra_media:
                    for i in range(len(extra_media)):
                        images_list.append([extra_media_paths[i], f'domains/postgram.ru/html/storage/app/uploads/stories/img/{extra_media[i]}'])

                await upload_file_to_server(images_list, 'cgi10.ipipe.ru', 22, 'alexman_ftp0', 'yIuSTGURtY55')

                connection.commit()
                print("Запись успешно добавлена в таблицу media.")

            if tags:
                for tag in tags:
                    tag = tag[1:]
                    tag_id = await get_tag(tag)
                    if tag_id != 0 and tag_id != -1:
                        placeholders = ', '.join(['%s'] * 5)
                        sql = f"INSERT INTO taggables (tag_id, taggable_id, taggable_type, created_at, updated_at) VALUES ({placeholders})"
                        cursor.execute(sql,
                                       (tag_id, story_id, 'App\\Models\\Story', data['created_at'], data['created_at']))
                        connection.commit()
                        print("Запись успешно добавлена в таблицу taggables.")
                    elif tag_id == -1:
                        print('Запись уже присутствует')
                    else:
                        placeholders = ', '.join(['%s'] * 4)
                        sql = f"INSERT INTO tags (name, normalized, created_at, updated_at) VALUES ({placeholders})"
                        cursor.execute(sql, (
                        tag, await clean_search_string(slugify(tag)), data['created_at'], data['created_at']))
                        tag_id = cursor.lastrowid
                        connection.commit()
                        print("Запись успешно добавлена в таблицу tags.")

                        placeholders = ', '.join(['%s'] * 5)
                        sql = f"INSERT INTO taggables (tag_id, taggable_id, taggable_type, created_at, updated_at) VALUES ({placeholders})"
                        cursor.execute(sql,
                                       (tag_id, story_id, 'App\\Models\\Story', data['created_at'], data['created_at']))
                        connection.commit()
                        print("Запись успешно добавлена в таблицу taggables.")

    except Error as e:
        print(f"Ошибка при подключении к MySQL: {e}")

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("Соединение с MySQL закрыто.")


async def add_data_to_server(message_info, channel_username):
    try:
        print('началась запись истории на сервер')
        data = {}
        media_data = {}
        tags_data = {}

        channel_name = urllib.parse.unquote(message_info['channel_link']).split('/')[-1]

        slideshowhtml = ''
        extra_media = []

        if message_info['message_title_media'] or message_info['extra_media']:
            for media in message_info['extra_media']:
                extra_media.append(f"{channel_name}-{os.path.basename(media)}")
            slideshowhtml = '''
                  <!-- Подключаем JS слайдера -->
                  <script defer src="/examples/libs/simple-adaptive-slider/simple-adaptive-slider.min.js"></script>
                  <script>
                    document.addEventListener('DOMContentLoaded', function () {
                      // инициализация слайдера
                      var slider = new SimpleAdaptiveSlider('.slider', {
                        loop: false,
                        autoplay: false,
                        interval: 5000,
                        swipe: true,
                      });
                    });
                    var WRAPPER_SELECTOR = ".slider__wrapper"
                      , ITEMS_SELECTOR = ".slider__items"
                      , ITEM_SELECTOR = ".slider__item"
                      , ITEM_CLASS_ACTIVE = "slider__item_active"
                      , CONTROL_SELECTOR = ".slider__control"
                      , CONTROL_CLASS_SHOW = "slider__control_show"
                      , INDICATOR_WRAPPER_ELEMENT = "ol"
                      , INDICATOR_WRAPPER_CLASS = "slider__indicators"
                      , INDICATOR_ITEM_ELEMENT = "li"
                      , INDICATOR_ITEM_CLASS = "slider__indicator"
                      , INDICATOR_ITEM_CLASS_ACTIVE = "slider__indicator_active"
                      , SWIPE_THRESHOLD = 20
                      , TRANSITION_NONE = "transition-none";
                    function SimpleAdaptiveSlider(t, i) {
                        for (var e in this._$root = document.querySelector(t),
                        this._$wrapper = this._$root.querySelector(WRAPPER_SELECTOR),
                        this._$items = this._$root.querySelector(ITEMS_SELECTOR),
                        this._$itemList = this._$root.querySelectorAll(ITEM_SELECTOR),
                        this._currentIndex = 0,
                        this._minOrder = 0,
                        this._maxOrder = 0,
                        this._$itemWithMinOrder = null,
                        this._$itemWithMaxOrder = null,
                        this._minTranslate = 0,
                        this._maxTranslate = 0,
                        this._direction = "next",
                        this._balancingItemsFlag = !1,
                        this._transform = 0,
                        this._hasSwipeState = !1,
                        this._swipeStartPosX = 0,
                        this._intervalId = null,
                        this._config = {
                            loop: !0,
                            autoplay: !1,
                            interval: 5e3,
                            swipe: !0
                        },
                        i)
                            this._config.hasOwnProperty(e) && (this._config[e] = i[e]);
                        for (var s = 0, n = this._$itemList.length; s < n; s++)
                            this._$itemList[s].dataset.order = s,
                            this._$itemList[s].dataset.index = s,
                            this._$itemList[s].dataset.translate = 0;
                        if (this._config.loop) {
                            var r = this._$itemList.length - 1
                              , a = 100 * -this._$itemList.length;
                            this._$itemList[r].dataset.order = -1,
                            this._$itemList[r].dataset.translate = 100 * -this._$itemList.length;
                            var o = "translateX(".concat(a, "%)");
                            this._$itemList[r].style.transform = o
                        }
                        this._addIndicators(),
                        this._refreshExtremeValues(),
                        this._setActiveClass(),
                        this._addEventListener(),
                        this._autoplay()
                    }
                    SimpleAdaptiveSlider.prototype._setActiveClass = function() {
                        var t, i, e, s;
                        for (t = 0,
                        i = this._$itemList.length; t < i; t++)
                            e = this._$itemList[t],
                            s = parseInt(e.dataset.index),
                            this._currentIndex === s ? e.classList.add(ITEM_CLASS_ACTIVE) : e.classList.remove(ITEM_CLASS_ACTIVE);
                        var n = this._$root.querySelectorAll("." + INDICATOR_ITEM_CLASS);
                        if (n.length)
                            for (t = 0,
                            i = n.length; t < i; t++)
                                e = n[t],
                                s = parseInt(e.dataset.slideTo),
                                this._currentIndex === s ? e.classList.add(INDICATOR_ITEM_CLASS_ACTIVE) : e.classList.remove(INDICATOR_ITEM_CLASS_ACTIVE);
                        var r = this._$root.querySelectorAll(CONTROL_SELECTOR);
                        if (r.length)
                            if (this._config.loop)
                                for (t = 0,
                                i = r.length; t < i; t++)
                                    r[t].classList.add(CONTROL_CLASS_SHOW);
                            else
                                0 === this._currentIndex ? (r[0].classList.remove(CONTROL_CLASS_SHOW),
                                r[1].classList.add(CONTROL_CLASS_SHOW)) : this._currentIndex === this._$itemList.length - 1 ? (r[0].classList.add(CONTROL_CLASS_SHOW),
                                r[1].classList.remove(CONTROL_CLASS_SHOW)) : (r[0].classList.add(CONTROL_CLASS_SHOW),
                                r[1].classList.add(CONTROL_CLASS_SHOW))
                    }
                    ,
                    SimpleAdaptiveSlider.prototype._move = function() {
                        if ("none" === this._direction)
                            return this._$items.classList.remove(TRANSITION_NONE),
                            void (this._$items.style.transform = "translateX(".concat(this._transform, "%)"));
                        if (!this._config.loop) {
                            if (this._currentIndex + 1 >= this._$itemList.length && "next" === this._direction)
                                return void this._autoplay("stop");
                            if (this._currentIndex <= 0 && "prev" === this._direction)
                                return
                        }
                        var t = "next" === this._direction ? -100 : 100
                          , i = this._transform + t;
                        "next" === this._direction ? ++this._currentIndex > this._$itemList.length - 1 && (this._currentIndex -= this._$itemList.length) : --this._currentIndex < 0 && (this._currentIndex += this._$itemList.length),
                        this._transform = i,
                        this._$items.style.transform = "translateX(".concat(i, "%)"),
                        this._setActiveClass()
                    }
                    ,
                    SimpleAdaptiveSlider.prototype._moveTo = function(t) {
                        var i = this._currentIndex;
                        this._direction = t > i ? "next" : "prev";
                        for (var e = 0; e < Math.abs(t - i); e++)
                            this._move()
                    }
                    ,
                    SimpleAdaptiveSlider.prototype._autoplay = function(t) {
                        if (this._config.autoplay)
                            return "stop" === t ? (clearInterval(this._intervalId),
                            void (this._intervalId = null)) : void (null === this._intervalId && (this._intervalId = setInterval(function() {
                                this._direction = "next",
                                this._move()
                            }
                            .bind(this), this._config.interval)))
                    }
                    ,
                    SimpleAdaptiveSlider.prototype._addIndicators = function() {
                        if (!this._$root.querySelector("." + INDICATOR_WRAPPER_CLASS)) {
                            var t = document.createElement(INDICATOR_WRAPPER_ELEMENT);
                            t.className = INDICATOR_WRAPPER_CLASS;
                            for (var i = 0, e = this._$itemList.length; i < e; i++) {
                                var s = document.createElement(INDICATOR_ITEM_ELEMENT);
                                s.className = INDICATOR_ITEM_CLASS,
                                s.dataset.slideTo = i,
                                t.appendChild(s)
                            }
                            this._$root.appendChild(t)
                        }
                    }
                    ,
                    SimpleAdaptiveSlider.prototype._refreshExtremeValues = function() {
                        var t = this._$itemList;
                        this._minOrder = parseInt(t[0].dataset.order),
                        this._maxOrder = this._minOrder,
                        this._$itemWithMinOrder = t[0],
                        this._$itemWithMaxOrder = this._$itemWithMinOrder,
                        this._minTranslate = parseInt(t[0].dataset.translate),
                        this._maxTranslate = this._minTranslate;
                        for (var i = 0, e = t.length; i < e; i++) {
                            var s = t[i]
                              , n = parseInt(s.dataset.order);
                            n < this._minOrder ? (this._minOrder = n,
                            this._$itemWithMinOrder = s,
                            this._minTranslate = parseInt(s.dataset.translate)) : n > this._maxOrder && (this._maxOrder = n,
                            this._$itemWithMaxOrder = s,
                            this._minTranslate = parseInt(s.dataset.translate))
                        }
                    }
                    ,
                    SimpleAdaptiveSlider.prototype._balancingItems = function() {
                        if (this._balancingItemsFlag) {
                            var t, i = this._$wrapper.getBoundingClientRect(), e = i.width / 2, s = this._$itemList.length;
                            if ("next" === this._direction) {
                                var n = i.left
                                  , r = this._$itemWithMinOrder;
                                t = this._minTranslate,
                                r.getBoundingClientRect().right < n - e && (r.dataset.order = this._minOrder + s,
                                t += 100 * s,
                                r.dataset.translate = t,
                                r.style.transform = "translateX(".concat(t, "%)"),
                                this._refreshExtremeValues())
                            } else if ("prev" === this._direction) {
                                var a = i.right
                                  , o = this._$itemWithMaxOrder;
                                t = this._maxTranslate,
                                o.getBoundingClientRect().left > a + e && (o.dataset.order = this._maxOrder - s,
                                t -= 100 * s,
                                o.dataset.translate = t,
                                o.style.transform = "translateX(".concat(t, "%)"),
                                this._refreshExtremeValues())
                            }
                            requestAnimationFrame(this._balancingItems.bind(this))
                        }
                    }
                    ,
                    SimpleAdaptiveSlider.prototype._addEventListener = function() {
                        var t = this._$items;
                        function i(t) {
                            this._autoplay("stop");
                            var i = 0 === t.type.search("touch") ? t.touches[0] : t;
                            this._swipeStartPosX = i.clientX,
                            this._swipeStartPosY = i.clientY,
                            this._hasSwipeState = !0,
                            this._hasSwiping = !1
                        }
                        function e(t) {
                            if (this._hasSwipeState) {
                                var i = 0 === t.type.search("touch") ? t.touches[0] : t
                                  , e = this._swipeStartPosX - i.clientX
                                  , s = this._swipeStartPosY - i.clientY;
                                if (!this._hasSwiping) {
                                    if (Math.abs(s) > Math.abs(e))
                                        return void (this._hasSwipeState = !1);
                                    this._hasSwiping = !0
                                }
                                t.preventDefault(),
                                this._config.loop || (this._currentIndex + 1 >= this._$itemList.length && e >= 0 && (e /= 4),
                                this._currentIndex <= 0 && e <= 0 && (e /= 4));
                                var n = e / this._$wrapper.getBoundingClientRect().width * 100
                                  , r = this._transform - n;
                                this._$items.classList.add(TRANSITION_NONE),
                                this._$items.style.transform = "translateX(".concat(r, "%)")
                            }
                        }
                        function s(t) {
                            if (this._hasSwipeState) {
                                var i = 0 === t.type.search("touch") ? t.changedTouches[0] : t
                                  , e = this._swipeStartPosX - i.clientX;
                                this._config.loop || (this._currentIndex + 1 >= this._$itemList.length && e >= 0 && (e /= 4),
                                this._currentIndex <= 0 && e <= 0 && (e /= 4));
                                var s = e / this._$wrapper.getBoundingClientRect().width * 100;
                                this._$items.classList.remove(TRANSITION_NONE),
                                s > SWIPE_THRESHOLD ? (this._direction = "next",
                                this._move()) : s < -SWIPE_THRESHOLD ? (this._direction = "prev",
                                this._move()) : (this._direction = "none",
                                this._move()),
                                this._hasSwipeState = !1,
                                this._config.loop && this._autoplay()
                            }
                        }
                        if (this._$root.addEventListener("click", function(t) {
                            var i = t.target;
                            if (this._autoplay("stop"),
                            i.classList.contains("slider__control"))
                                t.preventDefault(),
                                this._direction = i.dataset.slide,
                                this._move();
                            else if (i.dataset.slideTo) {
                                t.preventDefault();
                                var e = parseInt(i.dataset.slideTo);
                                this._moveTo(e)
                            }
                            this._config.loop && this._autoplay()
                        }
                        .bind(this)),
                        this._config.loop && (t.addEventListener("transitionstart", function() {
                            this._balancingItemsFlag = !0,
                            window.requestAnimationFrame(this._balancingItems.bind(this))
                        }
                        .bind(this)),
                        t.addEventListener("transitionend", function() {
                            this._balancingItemsFlag = !1
                        }
                        .bind(this))),
                        this._config.autoplay && (this._$root.addEventListener("mouseenter", function() {
                            this._autoplay("stop")
                        }
                        .bind(this)),
                        this._$root.addEventListener("mouseleave", function() {
                            this._config.loop && this._autoplay()
                        }
                        .bind(this))),
                        this._config.swipe) {
                            var n = !1;
                            try {
                                var r = Object.defineProperty({}, "passive", {
                                    get: function() {
                                        n = !0
                                    }
                                });
                                window.addEventListener("testPassiveListener", null, r)
                            } catch (t) {}
                            this._$root.addEventListener("touchstart", i.bind(this), !!n && {
                                passive: !1
                            }),
                            this._$root.addEventListener("touchmove", e.bind(this), !!n && {
                                passive: !1
                            }),
                            this._$root.addEventListener("mousedown", i.bind(this)),
                            this._$root.addEventListener("mousemove", e.bind(this)),
                            document.addEventListener("touchend", s.bind(this)),
                            document.addEventListener("mouseup", s.bind(this))
                        }
                        this._$root.addEventListener("dragstart", function(t) {
                            t.preventDefault()
                        }
                        .bind(this)),
                        document.addEventListener("visibilitychange", function() {
                            "hidden" === document.visibilityState ? this._autoplay("stop") : "visible" === document.visibilityState && this._config.loop && this._autoplay()
                        }
                        .bind(this))
                    }
                    ,
                    SimpleAdaptiveSlider.prototype.next = function() {
                        this._direction = "next",
                        this._move()
                    }
                    ,
                    SimpleAdaptiveSlider.prototype.prev = function() {
                        this._direction = "prev",
                        this._move()
                    }
                    ,
                    SimpleAdaptiveSlider.prototype.autoplay = function(t) {
                        this._autoplay("stop")
                    }
                    ;
                  </script>
                  
                <style>
                .slider {
                    position: relative;
                    overflow: hidden;
                    margin-left: auto;
                    margin-right: auto
                }
                
                .slider__wrapper {
                    position: relative;
                    overflow: hidden;
                    background-color: #eee
                }
                
                .slider__items {
                    display: flex;
                    transition: transform .5s ease
                }
                
                .transition-none {
                    transition: none
                }
                
                .slider__item {
                    flex: 0 0 100%;
                    max-width: 100%;
                    position: relative
                }
                
                .slider__control {
                    position: absolute;
                    top: 50%;
                    width: 40px;
                    height: 50px;
                    transform: translateY(-50%);
                    display: none;
                    align-items: center;
                    justify-content: center;
                    color: #fff;
                    background: rgba(0,0,0,.3);
                    opacity: .5;
                    user-select: none
                }
                
                .slider__control_show {
                    display: flex
                }
                
                .slider__control:focus,.slider__control:hover {
                    color: #fff;
                    text-decoration: none;
                    opacity: .7
                }
                
                .slider__control_prev {
                    left: 0
                }
                
                .slider__control_next {
                    right: 0
                }
                
                .slider__control::before {
                    content: '';
                    display: inline-block;
                    width: 20px;
                    height: 20px;
                    background: transparent no-repeat center center;
                    background-size: 100% 100%
                }
                
                .slider__control_prev::before {
                    background-image: url("data:image/svg+xml;charset=utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='%23fff' viewBox='0 0 8 8'%3E%3Cpath d='M5.25 0l-4 4 4 4 1.5-1.5-2.5-2.5 2.5-2.5-1.5-1.5z'/%3E%3C/svg%3E")
                }
                
                .slider__control_next::before {
                    background-image: url("data:image/svg+xml;charset=utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='%23fff' viewBox='0 0 8 8'%3E%3Cpath d='M2.75 0l-1.5 1.5 2.5 2.5-2.5 2.5 1.5 1.5 4-4-4-4z'/%3E%3C/svg%3E")
                }
                
                .slider__indicators {
                    position: absolute;
                    left: 0;
                    right: 0;
                    bottom: 30px;
                    display: flex;
                    justify-content: center;
                    padding-left: 0;
                    margin: 0 15%;
                    list-style: none;
                    user-select: none;
                    column-gap: 3px;
                }
                
                .slider__indicator {
                    flex: 0 1 auto;
                    width: 10px;
                    height: 4px;
                    margin-right: 3px;
                    border-radius: 100%;
                    margin-left: 3px;
                    background-color: rgb(80 80 80 / 50%);
                    background-clip: padding-box;
                    border-top: 10px solid #939393;
                    cursor: pointer;
                }
                
                .slider__indicator_active {
                    border-top: 10px solid #fff;
                }
    
            
                /* дополнительные стили для этого примера */
                .slider__items {
                  counter-reset: slide;
                }
            
                .slider__item {
                  counter-increment: slide;
                  height: 400px;
                  background-color: white;
                  display: flex;
                  justify-content: center;
                }
                
                img, video {
                    object-fit: contain;
                }
            
                .slider__item>div::before {
                  content: counter(slide);
                  position: absolute;
                  top: 10px;
                  right: 20px;
                  color: #fff;
                  font-style: italic;
                  font-size: 32px;
                  font-weight: bold;
                }
                
                .custom_class {
                    display: none;
                }
              </style>
                ''' + f'''
                <div class="container" style="max-width: 100%;">
                  <div class="slider">
                    <div class="slider__wrapper">
                      <div class="slider__items">
                  {f'<div class="slider__item"><img src="https://postgram.ru/uploads/stories/img/{channel_name}-{os.path.basename(message_info["message_title_media"])}"></div>' if message_info["message_title_media"].split('.')[-1] != 'mp4' else f'<div class="slider__item"><video src="https://postgram.ru/uploads/stories/img/{channel_name}-{os.path.basename(message_info["message_title_media"])}" controls></video></div>'}
                  {" ".join([f'<div class="slider__item"><img src="https://postgram.ru/uploads/stories/img/{media}"></div>' if media.split('.')[-1] != 'mp4' else f'<div class="slider__item"><video src="https://postgram.ru/uploads/stories/img/{media}" controls></video></div>' for media in extra_media])}
                      </div>
                    </div>
                    <a class="slider__control slider__control_prev" href="#" role="button" data-slide="prev" style="color: white; border: 0;"></a>
                    {'<a class="slider__control slider__control_next" href="#" role="button" data-slide="next" style="color: white; border: 0;"></a>' if extra_media else ''}
                    <ol class="slider__indicators">{" ".join([f'<li class="slider__indicator" data-slide-to="{i}"></li>' for i in range(len(extra_media) + 1 if extra_media else 0)])}</ol>
                  </div>
                </div>
                ''' + '''
                '''
        tags = list(filter(lambda x: x[0] == '#', message_info['message_text'].split()))
        for tag in tags:
            message_info['message_text'] = message_info['message_text'].replace(tag, '')
            message_info['message_without_url'] = message_info['message_without_url'].replace(tag, '')

        user_name = urllib.parse.unquote(message_info['user_link']).split('/')[-1]
        user_id, community_id = await get_user_id_and_community_id(user_name, channel_name)
        data['user_id'], data['community_id'] = user_id, community_id

        title = message_info['message_text'].split('\n')[0]
        data['title'] = title[:155] + '...' if len(title) > 158 else title
        data['subtitle'] = ''
        data['slug'] = (await clean_search_string(slugify(data['title'])) + str(random.randint(1, 100000))).replace(' ', '-').lower()


        text = []
        for line in message_info['message_text'].split('\n'):
            if len(line) > 5:
                text.append(line)

        text_without_url = []
        for line in message_info['message_without_url'].split('\n'):
            if len(line) > 4:
                text_without_url.append(line)

        if len(text_without_url) >= 4:
            data['summary'] = '\n'.join(text_without_url[1:4])
        else:
            data['summary'] = '\n'.join(text_without_url[1:])
        data['body'] = json.dumps({
            "time": int(message_info['message_date'].timestamp() * 1000),
            "version": "2.28.2",
        })
        data['body_rendered'] = slideshowhtml + '\n'.join(list(map(lambda x: f'<p class="w-content">{x}</p>', text[1:])))
        data['published_at'] = message_info['message_date']
        data['created_at'] = message_info['message_date']


        if message_info['message_title_media']:
            media_data['model_type'] = 'App\\Models\\Story'
            media_data['uuid'] = str(uuid.uuid4())
            if os.path.basename(message_info['message_title_media']).split('.')[-1] == 'mp4':
                media_data['collection_name'] = 'featured-video'
            else:
                media_data['collection_name'] = 'featured-image'
            media_data['name'] = f"{channel_name}-{os.path.basename(message_info['message_title_media']).split('.')[0]}"
            media_data['file_name'] = f"{channel_name}-{os.path.basename(message_info['message_title_media'])}"
            media_data['mime_type'] = 'image/jpeg'
            media_data['disk'] = 'local'
            media_data['size'] = os.path.getsize(message_info['message_title_media'])
            media_data['manipulations'] = json.dumps([])
            media_data['custom_properties'] = json.dumps([])
            media_data['generated_conversions'] = json.dumps([])
            media_data['responsive_images'] = json.dumps([])
            media_data['order_column'] = 1

        await insert_record(data, media_data, tags, message_info['message_title_media'], extra_media, message_info['extra_media'])
    except Exception as e:
        print(e)
