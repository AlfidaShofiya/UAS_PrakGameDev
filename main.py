from math import sin, cos, pi
from random import randint, choice, random
import sys

from direct.gui.OnscreenText import OnscreenText
from direct.interval.MetaInterval import Sequence
from direct.interval.FunctionInterval import Wait, Func
from direct.showbase.ShowBase import ShowBase
from direct.task.Task import Task
from panda3d.core import TextNode, TransparencyAttrib
from panda3d.core import LPoint3, LVector3


SPRITE_POS = 55
SCREEN_X = 20
SCREEN_Y = 15
TURN_RATE = 360
ACCELERATION = 10
MAX_VEL = 6
MAX_VEL_SQ = MAX_VEL ** 2
DEG_TO_RAD = pi / 180
BULLET_LIFE = 2
BULLET_REPEAT = .2
BULLET_SPEED = 10
AST_INIT_VEL = 1
AST_INIT_SCALE = 3
AST_VEL_SCALE = 2.2
AST_SIZE_SCALE = .6
AST_MIN_SCALE = 1.1



def loadObject(tex=None, pos=LPoint3(0, 0), depth=SPRITE_POS, scale=1,
               transparency=True):
    # Setiap objek menggunakan model pesawat dan di-parent ke kamera
    # sehingga menghadap ke layar.
    obj = base.loader.loadModel("models/plane")
    obj.reparentTo(base.camera)

    # Atur posisi dan skala awal.
    obj.setPos(pos.getX(), depth, pos.getY())
    obj.setScale(scale)

    # Ini memberi tahu Panda untuk tidak khawatir tentang urutan hal-hal yang ditarik
    # (mis. nonaktifkan pengujian Z). Ini mencegah efek yang dikenal sebagai Z-pertarungan.
    obj.setBin("unsorted", 0)
    obj.setDepthTest(False)

    if transparency:
        # Aktifkan pencampuran transparansi.
        obj.setTransparency(TransparencyAttrib.MAlpha)

    if tex:
        # Muat dan atur tekstur yang diminta.
        tex = base.loader.loadTexture("textures/" + tex)
        obj.setTexture(tex, 1)

    return obj


# Fungsi seperti makro yang digunakan untuk mengurangi jumlah kode yang diperlukan untuk membuat
# di layar petunjuk
def genLabelText(text, i):
    return OnscreenText(text=text, parent=base.a2dTopLeft, pos=(0.07, -.06 * i - 0.1),
                        fg=(1, 1, 1, 1), align=TextNode.ALeft, shadow=(0, 0, 0, 0.5), scale=.05)


class AsteroidsDemo(ShowBase):

    def __init__(self):
        # Inisialisasi kelas ShowBase dari mana kita mewarisi, yang akan
        # buat jendela dan atur semua yang kita butuhkan untuk rendering ke dalamnya.
        ShowBase.__init__(self)

        # Kode ini menempatkan judul standar dan teks instruksi di layar
        self.title = OnscreenText(text="ANIMALHUNTER",
                                  parent=base.a2dBottomRight, scale=.07,
                                  align=TextNode.ARight, pos=(-0.1, 0.1),
                                  fg=(1, 1, 1, 1), shadow=(0, 0, 0, 0.5))
        self.escapeText = genLabelText("ESC: Keluar", 0)
        self.leftkeyText = genLabelText("Memutar Kekiri: Panah Kiri", 1)
        self.rightkeyText = genLabelText("Memutar Kekanan: Panah Kanan", 2)
        self.upkeyText = genLabelText("Tambah Kecepatan: Panah Atas", 3)
        self.spacekeyText = genLabelText("Tembak: Spasi", 4)

        # Nonaktifkan kontrol kamera berbasis mouse default. Ini adalah metode pada
        # Kelas ShowBase dari mana kita mewarisi.
        self.disableMouse()

        # Muat bidang bintang latar belakang.
        self.setBackgroundColor((0, 0, 0, 1))
        self.bg = loadObject("pemandangan.jpg", scale=146, depth=200,
                             transparency=False)

        # Muat kapal dan atur kecepatan awalnya.
        self.ship = loadObject("pistol.png")
        self.setVelocity(self.ship, LVector3.zero())

        # Kamus tentang tombol apa yang sedang ditekan
        # Peristiwa penting memperbarui daftar ini, dan tugas kita akan menanyakannya sebagai masukan
        self.keys = {"turnLeft": 0, "turnRight": 0,
                     "accel": 0, "fire": 0}

        self.accept("escape", sys.exit)  # Melarikan diri berhenti
        # Acara kunci lainnya menetapkan nilai yang sesuai dalam kamus kunci kami
        self.accept("arrow_left",     self.setKey, ["turnLeft", 1])
        self.accept("arrow_left-up",  self.setKey, ["turnLeft", 0])
        self.accept("arrow_right",    self.setKey, ["turnRight", 1])
        self.accept("arrow_right-up", self.setKey, ["turnRight", 0])
        self.accept("arrow_up",       self.setKey, ["accel", 1])
        self.accept("arrow_up-up",    self.setKey, ["accel", 0])
        self.accept("space",          self.setKey, ["fire", 1])

        # Sekarang kita membuat tugas. taskMgr adalah pengelola tugas yang sebenarnya
        # memanggil fungsi setiap frame. Metode add membuat tugas baru.
        # Argumen pertama adalah fungsi yang akan dipanggil, dan yang kedua
        # argumen adalah nama untuk tugas. Ini mengembalikan objek tugas yang
        # diteruskan ke fungsi setiap frame.
        self.gameTask = base.taskMgr.add(self.gameLoop, "gameLoop")

        # Menyimpan waktu di mana peluru berikutnya dapat ditembakkan.
        self.nextBullet = 0.0

        # Daftar ini akan menyimpan peluru yang ditembakkan.
        self.bullets = []

        # Inisialisasi lengkap dengan menelurkan asteroid.
        self.spawnAsteroids()

    # Seperti dijelaskan sebelumnya, ini hanya menetapkan kunci dalam kamus self.keys
    # ke nilai yang diberikan.
    def setKey(self, key, val):
        self.keys[key] = val

    def setVelocity(self, obj, val):
        obj.setPythonTag("velocity", val)

    def getVelocity(self, obj):
        return obj.getPythonTag("velocity")

    def setExpires(self, obj, val):
        obj.setPythonTag("expires", val)

    def getExpires(self, obj):
        return obj.getPythonTag("expires")

    def spawnAsteroids(self):
        # Variabel kontrol jika kapal masih hidup
        self.alive = True
        self.asteroids = []  # Daftar yang akan berisi asteroid kami

        for i in range(10):
            # Ini memuat asteroid. Tekstur yang dipilih adalah acak
            # dari "asteroid1.png" ke "asteroid3.png"
            asteroid = loadObject("animal%d.png" % (randint(1, 3)),
                                  scale=AST_INIT_SCALE)
            self.asteroids.append(asteroid)

            # Ini semacam peretasan, tetapi itu membuat asteroid tidak bertelur
            # dekat pemain. Itu membuat daftar (-20, -19 ... -5, 5, 6, 7,
            # ... 20) dan memilih nilai darinya. Karena pemain mulai dari 0
            # dan daftar ini tidak berisi apa pun dari -4 hingga 4, itu tidak akan
            # dekat dengan pemain.
            asteroid.setX(choice(tuple(range(-SCREEN_X, -5)) + tuple(range(5, SCREEN_X))))
            # Hal yang sama untuk Y
            asteroid.setZ(choice(tuple(range(-SCREEN_Y, -5)) + tuple(range(5, SCREEN_Y))))

            # Pos adalah sudut acak dalam radian
            heading = random() * 2 * pi

            # Mengubah judul menjadi vektor dan mengalikannya dengan kecepatan menjadi
            # mendapatkan vektor kecepatan
            v = LVector3(sin(heading), 0, cos(heading)) * AST_INIT_VEL
            self.setVelocity(self.asteroids[i], v)

    # Ini adalah fungsi tugas utama kami, yang melakukan semua per-frame
    # pengolahan. Dibutuhkan dalam diri seperti semua fungsi di kelas, dan tugas,
    # objek tugas dikembalikan oleh taskMgr.
    def gameLoop(self, task):
        # Dapatkan waktu yang berlalu sejak frame berikutnya. Kami membutuhkan ini untuk kami
        # perhitungan jarak dan kecepatan.
        dt = globalClock.getDt()

        # Jika kapal tidak hidup, jangan lakukan apa pun. Tugas mengembalikan Task.cont ke
        # menandakan bahwa tugas harus terus berjalan. Jika Task.done adalah
        # sebagai gantinya, tugas akan dihapus dan tidak akan lagi
        # disebut setiap frame.
        if not self.alive:
            return Task.cont

        # perbarui posisi kapal
        self.updateShip(dt)

        # periksa untuk melihat apakah kapal dapat menembak
        if self.keys["fire"] and task.time > self.nextBullet:
            self.fire(task.time)  # Jika demikian, panggil fungsi api
            # Dan nonaktifkan penembakan sebentar
            self.nextBullet = task.time + BULLET_REPEAT
        # Hapus bendera api sampai tekan spasi berikutnya
        self.keys["fire"] = 0

        # perbarui asteroid
        for obj in self.asteroids:
            self.updatePos(obj, dt)

        # perbarui peluru
        newBulletArray = []
        for obj in self.bullets:
            self.updatePos(obj, dt)  # Perbarui peluru
            # Peluru memiliki waktu experation (lihat definisi api)
            # Jika peluru belum kedaluwarsa, tambahkan ke daftar peluru baru jadi
            # bahwa itu akan terus ada.
            if self.getExpires(obj) > task.time:
                newBulletArray.append(obj)
            else:
                obj.removeNode()  # Jika tidak, hapus dari tempat kejadian.
        # Setel larik peluru menjadi larik yang baru diperbarui
        self.bullets = newBulletArray

        # Periksa tabrakan peluru dengan asteroid
        # Singkatnya, ia memeriksa setiap peluru terhadap setiap asteroid. Ini
        # cukup lambat. Pengoptimalan besar adalah mengurutkan objek yang tersisa untuk
        # kanan dan periksa hanya jika mereka tumpang tindih. Framerate bisa turun jika
        # ada banyak peluru di layar, tetapi sebagian besar tidak apa-apa.
        for bullet in self.bullets:
            # Pernyataan jangkauan ini membuatnya melangkah melalui daftar asteroid
            # ke belakang. Ini karena jika asteroid dihilangkan,
            # elemen setelah itu akan mengubah posisi dalam daftar. Jika kau pergi
            # mundur, panjangnya tetap.
            for i in range(len(self.asteroids) - 1, -1, -1):
                asteroid = self.asteroids[i]
                # Deteksi tabrakan Panda lebih rumit dari yang kita butuhkan
                # di sini. Ini adalah pemeriksaan tumbukan bola dasar. jika
                # jarak antara pusat-pusat objek kurang dari jumlah
                # jari-jari kedua benda, maka terjadi tumbukan. Kita gunakan
                # lengthSquared() karena lebih cepat dari length().
                if ((bullet.getPos() - asteroid.getPos()).lengthSquared() <
                    (((bullet.getScale().getX() + asteroid.getScale().getX())
                      * .5) ** 2)):
                    # Jadwalkan peluru untuk dihapus
                    self.setExpires(bullet, 0)
                    self.asteroidHit(i)      # Tangani pukulannya

        # Sekarang kita melakukan tabrakan yang sama untuk kapal
        shipSize = self.ship.getScale().getX()
        for ast in self.asteroids:
            # Pemeriksaan tabrakan bola yang sama untuk kapal vs. asteroid
            if ((self.ship.getPos() - ast.getPos()).lengthSquared() <
                    (((shipSize + ast.getScale().getX()) * .5) ** 2)):
                # Jika ada hit, bersihkan layar dan jadwalkan restart
                self.alive = False         # Kapal tidak lagi hidup
                # Hapus setiap objek di asteroid dan peluru dari tempat kejadian
                for i in self.asteroids + self.bullets:
                    i.removeNode()
                self.bullets = []          # Hapus daftar peluru
                self.ship.hide()           # Sembunyikan kapalnya
                # Atur ulang kecepatan
                self.setVelocity(self.ship, LVector3(0, 0, 0))
                Sequence(Wait(2),          # Tunggu 2 detik
                         Func(self.ship.setR, 0),  # Setel ulang judul
                         Func(self.ship.setX, 0),  # Atur ulang posisi X
                         # Atur ulang posisi Y (Z untuk Panda)
                         Func(self.ship.setZ, 0),
                         Func(self.ship.show),     # Tunjukkan kapalnya
                         Func(self.spawnAsteroids)).start()  # Membuat ulang asteroid
                return Task.cont

        # Jika pemain telah berhasil menghancurkan semua asteroid, respawn mereka
        if len(self.asteroids) == 0:
            self.spawnAsteroids()

        return Task.cont    # Karena setiap pengembalian adalah Task.cont, tugas akan
        # lanjutkan tanpa batas

    # Memperbarui posisi objek
    def updatePos(self, obj, dt):
        vel = self.getVelocity(obj)
        newPos = obj.getPos() + (vel * dt)

        # Periksa apakah objek berada di luar batas. Jika demikian, bungkus
        radius = .5 * obj.getScale().getX()
        if newPos.getX() - radius > SCREEN_X:
            newPos.setX(-SCREEN_X)
        elif newPos.getX() + radius < -SCREEN_X:
            newPos.setX(SCREEN_X)
        if newPos.getZ() - radius > SCREEN_Y:
            newPos.setZ(-SCREEN_Y)
        elif newPos.getZ() + radius < -SCREEN_Y:
            newPos.setZ(SCREEN_Y)

        obj.setPos(newPos)

    # Pawang saat asteroid terkena peluru
    def asteroidHit(self, index):
        # Jika asteroid itu kecil, maka asteroid itu akan disingkirkan saja
        if self.asteroids[index].getScale().getX() <= AST_MIN_SCALE:
            self.asteroids[index].removeNode()
            # Hapus asteroid dari daftar asteroid.
            del self.asteroids[index]
        else:
            # Jika cukup besar, bagilah menjadi asteroid-asteroid kecil.
            # Pertama kami memperbarui asteroid saat ini.
            asteroid = self.asteroids[index]
            newScale = asteroid.getScale().getX() * AST_SIZE_SCALE
            asteroid.setScale(newScale)  # Skalakan ulang

            # Arah baru dipilih tegak lurus dengan arah lama
            # Ini ditentukan dengan menggunakan produk silang, yang mengembalikan a
            # vektor tegak lurus terhadap dua vektor input. Dengan menyeberang
            # kecepatan dengan vektor yang masuk ke layar, kita mendapatkan vektor
            # yang orthagonal dengan kecepatan awal di bidang layar.
            vel = self.getVelocity(asteroid)
            speed = vel.length() * AST_VEL_SCALE
            vel.normalize()
            vel = LVector3(0, 1, 0).cross(vel)
            vel *= speed
            self.setVelocity(asteroid, vel)

            # Sekarang kami membuat asteroid baru yang identik dengan yang sekarang
            newAst = loadObject(scale=newScale)
            self.setVelocity(newAst, vel * -1)
            newAst.setPos(asteroid.getPos())
            newAst.setTexture(asteroid.getTexture(), 1)
            self.asteroids.append(newAst)

    # Ini memperbarui posisi kapal. Ini mirip dengan pembaruan umum
    # tetapi memperhitungkan belokan dan dorong
    def updateShip(self, dt):
        heading = self.ship.getR()  # Judul adalah nilai gulungan untuk model ini
        # Ubah judul jika kiri atau kanan ditekan
        if self.keys["turnRight"]:
            heading += dt * TURN_RATE
            self.ship.setR(heading % 360)
        elif self.keys["turnLeft"]:
            heading -= dt * TURN_RATE
            self.ship.setR(heading % 360)

        # Dorongan menyebabkan percepatan ke arah kapal saat ini
        # menghadapi
        if self.keys["accel"]:
            heading_rad = DEG_TO_RAD * heading
            # Ini membangun vektor kecepatan baru dan menambahkannya ke vektor saat ini
            # relatif terhadap kamera, layar di Panda adalah bidang XZ.
            # Oleh karena itu semua nilai Y kami dalam kecepatan kami adalah 0 untuk menandakan
            # tidak ada perubahan ke arah itu.
            newVel = \
                LVector3(sin(heading_rad), 0, cos(heading_rad)) * ACCELERATION * dt
            newVel += self.getVelocity(self.ship)
            # Menjepit kecepatan baru ke kecepatan maksimum. panjangSquared() adalah
            # digunakan lagi karena lebih cepat dari panjang()
            if newVel.lengthSquared() > MAX_VEL_SQ:
                newVel.normalize()
                newVel *= MAX_VEL
            self.setVelocity(self.ship, newVel)

        # Terakhir, perbarui posisinya seperti objek lainnya
        self.updatePos(self.ship, dt)

    # Membuat peluru dan menambahkannya ke daftar peluru
    def fire(self, time):
        direction = DEG_TO_RAD * self.ship.getR()
        pos = self.ship.getPos()
        bullet = loadObject("bullet.png", scale=.2)  # Buat objeknya
        bullet.setPos(pos)
        # Kecepatan berbanding lurus dengan kapal
        vel = (self.getVelocity(self.ship) +
               (LVector3(sin(direction), 0, cos(direction)) *
                BULLET_SPEED))
        self.setVelocity(bullet, vel)
        # Atur waktu kedaluwarsa peluru menjadi jumlah tertentu melewati
        # waktu saat ini
        self.setExpires(bullet, time + BULLET_LIFE)

        # Akhirnya, tambahkan peluru baru ke daftar
        self.bullets.append(bullet)

demo = AsteroidsDemo()
demo.run()
