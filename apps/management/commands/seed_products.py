import random

from django.core.management.base import BaseCommand

from apps.models import Category, Product

CATEGORIES = [
    {"slug": "elektronika", "title": "Elektronika", "icon": "icon_elektronika.png"},
    {"slug": "kiyim-kechak", "title": "Kiyim-kechak", "icon": "icon_kiyim-kechak.png"},
    {"slug": "kosmetika", "title": "Kosmetika", "icon": "icon_kosmetika.png"},
    {"slug": "oziq-ovqat", "title": "Oziq-ovqat", "icon": "icon_oziq-ovqat.png"},
    {"slug": "kitoblar", "title": "Kitoblar", "icon": "icon_kitoblar.png"},
    {"slug": "bolalar-dunyosi", "title": "Bolalar dunyosi", "icon": "icon_bolalar-dunyosi.png"},
    {"slug": "sport-va-dam-olish", "title": "Sport va dam olish", "icon": "icon_sport-va-dam-olish.png"},
    {"slug": "uy-va-bog", "title": "Uy va bog'", "icon": "icon_uy-va-bog.png"},
    {"slug": "mebel", "title": "Mebel", "icon": "icon_mebel.png"},
    {"slug": "zargarlik-va-soatlar", "title": "Zargarlik va soatlar", "icon": "icon_zargarlik-va-soatlar.png"},
    {"slug": "avto-aksessuarlar", "title": "Avto aksessuarlar", "icon": "icon_avto-aksessuarlar.png"},
    {"slug": "maishiy-texnika", "title": "Maishiy texnika", "icon": "icon_maishiy-texnika.png"},
]

# (slug, title, category_slug, price, delivery_price, stock, image_filename, description)
PRODUCTS = [
    ("acer-nitro-v15", "Acer Nitro V15 noutbuk", "elektronika", 12_500_000, 30_000, 8,
     "acer-nitro-v15.jpg", "O'yinlar va ish uchun quvvatli noutbuk, RTX videokarta bilan."),
    ("airpods-pro-2", "Apple AirPods Pro 2", "elektronika", 2_800_000, 20_000, 25,
     "airpods-pro-2.jpg", "Shovqinni bostirish funksiyasiga ega simsiz quloqchinlar."),
    ("apple-watch-series-9", "Apple Watch Series 9", "elektronika", 5_200_000, 25_000, 12,
     "apple-watch-series-9.jpg", "Sog'liqni kuzatish va bildirishnomalar uchun aqlli soat."),
    ("iphone-15-pro-max", "iPhone 15 Pro Max 256GB", "elektronika", 16_800_000, 30_000, 6,
     "iphone-15-pro-max.jpg", "Titan korpusli, A17 Pro chipli flagman smartfon."),
    ("macbook-air-m2", "MacBook Air M2 13\"", "elektronika", 14_900_000, 30_000, 5,
     "macbook-air-m2.jpg", "Yengil va kuchli, M2 protsessorli noutbuk."),
    ("samsung-galaxy-s24-ultra", "Samsung Galaxy S24 Ultra", "elektronika", 13_500_000, 30_000, 9,
     "samsung-galaxy-s24-ultra.jpg", "S Pen bilan keladigan yuqori unumli flagman smartfon."),
    ("sony-playstation-5", "Sony PlayStation 5", "elektronika", 7_900_000, 30_000, 7,
     "sony-playstation-5.jpg", "Yangi avlod o'yin konsoli, 4K grafika qo'llab-quvvatlanadi."),
    ("xiaomi-redmi-note-13-pro", "Xiaomi Redmi Note 13 Pro", "elektronika", 3_600_000, 20_000, 20,
     "xiaomi-redmi-note-13-pro.jpg", "Yaxshi kamerali va uzoq batareya quvvatiga ega smartfon."),

    ("avto-videoregistrator", "Avtomobil videoregistratori 4K", "avto-aksessuarlar", 890_000, 25_000, 15,
     "avto-videoregistrator.jpg", "Tungi rejimga ega, 4K sifatda video yozib oluvchi qurilma."),
    ("magicar-906-signalizatsiya", "Magicar 906 avtomobil signalizatsiyasi", "avto-aksessuarlar", 1_250_000, 25_000, 10,
     "magicar-906-signalizatsiya.jpg", "Ikki tomonlama aloqali, avtoyurgizish funksiyali signalizatsiya."),

    ("artel-konditsioner-12", "Artel konditsioner 12000 BTU", "maishiy-texnika", 4_200_000, 60_000, 10,
     "artel-konditsioner-12.jpg", "Issiq va sovuq rejimli, quvvatli inverter konditsioner."),
    ("bosch-changyutgich", "Bosch changyutgich", "maishiy-texnika", 1_650_000, 30_000, 14,
     "bosch-changyutgich.jpg", "Yuqori so'rish kuchiga ega, uy uchun qulay changyutgich."),
    ("lg-kir-yuvish-mashinasi", "LG kir yuvish mashinasi 7kg", "maishiy-texnika", 4_800_000, 60_000, 8,
     "lg-kir-yuvish-mashinasi.jpg", "Avtomatik dasturlarga ega, tejamkor kir yuvish mashinasi."),
    ("mikrotolqinli-pech", "Mikrotolqinli pech 23L", "maishiy-texnika", 1_350_000, 30_000, 16,
     "mikrotolqinli-pech.jpg", "Isitish va erittirish rejimlariga ega mikrotolqinli pech."),
    ("philips-dazmol", "Philips bug'li dazmol", "maishiy-texnika", 480_000, 20_000, 22,
     "philips-dazmol.jpg", "Kuchli bug' oqimi bilan tez va sifatli dazmollash."),
    ("samsung-muzlatkich", "Samsung muzlatkich Side-by-Side", "maishiy-texnika", 9_500_000, 80_000, 4,
     "samsung-muzlatkich.jpg", "Keng hajmli, No Frost texnologiyali zamonaviy muzlatkich."),

    ("adidas-sport-kostyumi", "Adidas sport kostyumi", "kiyim-kechak", 650_000, 25_000, 30,
     "adidas-sport-kostyumi.jpg", "Sifatli matodan tikilgan, kundalik va sport uchun qulay kostyum."),
    ("ayollar-yozgi-koylagi", "Ayollar yozgi ko'ylagi", "kiyim-kechak", 220_000, 20_000, 35,
     "ayollar-yozgi-koylagi.jpg", "Yengil va nafis mato, yoz fasli uchun mos ko'ylak."),
    ("erkaklar-klassik-shimi", "Erkaklar klassik shimi", "kiyim-kechak", 280_000, 20_000, 28,
     "erkaklar-klassik-shimi.jpg", "Ish va rasmiy tadbirlar uchun qulay klassik shim."),
    ("erkaklar-qishki-kurtkasi", "Erkaklar qishki kurtkasi", "kiyim-kechak", 750_000, 25_000, 18,
     "erkaklar-qishki-kurtkasi.jpg", "Sovuqdan yaxshi himoya qiladigan issiq qishki kurtka."),
    ("qishki-shapka-qora", "Qishki shapka (qora)", "kiyim-kechak", 95_000, 15_000, 40,
     "qishki-shapka-qora.jpg", "Yumshoq va issiq, qishki kunlar uchun mos shapka."),
    ("nike-air-force", "Nike Air Force 1 krossovkasi", "kiyim-kechak", 890_000, 25_000, 20,
     "nike-air-force.jpg", "Klassik dizaynli, kundalik kiyish uchun qulay krossovka."),

    ("chanel-ayollar-atiri", "Chanel ayollar atiri", "kosmetika", 1_450_000, 20_000, 12,
     "chanel-ayollar-atiri.jpg", "Nafis va uzoq saqlanadigan hidga ega ayollar atiri."),
    ("dior-sauvage-atiri", "Dior Sauvage erkaklar atiri", "kosmetika", 1_650_000, 20_000, 12,
     "dior-sauvage-atiri.jpg", "Erkaklar uchun kuchli va sharobat hidli atir."),
    ("loreal-yuz-kremi", "L'Oreal yuz kremi", "kosmetika", 185_000, 15_000, 25,
     "loreal-yuz-kremi.jpg", "Teri namligini saqlab turuvchi kunduzgi yuz kremi."),
    ("maybelline-tush", "Maybelline tush (kirpik bo'yog'i)", "kosmetika", 95_000, 15_000, 30,
     "maybelline-tush.jpg", "Hajm beruvchi va suvga chidamli kirpik bo'yog'i."),
    ("nivea-dush-geli", "Nivea dush geli 250ml", "kosmetika", 65_000, 15_000, 40,
     "nivea-dush-geli.jpg", "Teri uchun yumshoq va yoqimli hidli dush geli."),

    ("borges-zaytun-yogi-1l", "Borges zaytun yog'i 1L", "oziq-ovqat", 145_000, 20_000, 20,
     "borges-zaytun-yogi-1l.jpg", "Ispaniyadan olib kelingan, sof zaytun yog'i."),
    ("ferrero-rocher-shokoladi", "Ferrero Rocher shokoladi (16 dona)", "oziq-ovqat", 135_000, 15_000, 25,
     "ferrero-rocher-shokoladi.jpg", "Sovg'a uchun ham mos, mazali yong'oqli shokolad to'plami."),
    ("haqiqiy-tog-asali-1-kg", "Haqiqiy tog' asali 1kg", "oziq-ovqat", 180_000, 20_000, 18,
     "haqiqiy-tog-asali-1-kg.jpg", "Tog' o'simliklaridan yig'ilgan tabiiy asal."),
    ("qora-choy-keniya-500g", "Qora choy Keniya 500g", "oziq-ovqat", 68_000, 15_000, 30,
     "qora-choy-keniya-500g.jpg", "Boy ta'mga ega, yuqori sifatli qora choy."),

    ("alkimyogar-koelyo", "Alkimyogar - Paulo Koelyo", "kitoblar", 55_000, 15_000, 20,
     "alkimyogar-koelyo.jpg", "Dunyo bestselleriga aylangan mashhur falsafiy roman."),
    ("boy-ota-kambagal-ota", "Boy ota, kambag'al ota - Robert Kiyosaki", "kitoblar", 62_000, 15_000, 22,
     "boy-ota-kambagal-ota.jpg", "Moliyaviy savodxonlik bo'yicha mashhur kitob."),
    ("jeyms-klir-atom-odatlar", "Atom odatlar - Jeyms Klir", "kitoblar", 58_000, 15_000, 24,
     "jeyms-klir-atom-odatlar.jpg", "Kichik odatlar orqali katta natijalarga erishish haqida kitob."),
    ("python-darsligi", "Python dasturlash tili darsligi", "kitoblar", 85_000, 15_000, 15,
     "python-darsligi.jpg", "Dasturlashni noldan o'rganish uchun amaliy qo'llanma."),
    ("stiv-jobs-biografiyasi", "Stiv Jobs biografiyasi - Uolter Ayzekson", "kitoblar", 72_000, 15_000, 14,
     "stiv-jobs-biografiyasi.jpg", "Apple asoschisining hayoti haqida batafsil biografiya."),

    ("bolalar-kolyaskasi-3-in-1", "Bolalar aravachasi 3-in-1", "bolalar-dunyosi", 2_400_000, 40_000, 6,
     "bolalar-kolyaskasi-3-in-1.jpg", "Chaqaloqlar uchun qulay va ko'p funksiyali aravacha."),
    ("katta-ayiqcha-150-sm", "Katta pluş ayiqcha 150sm", "bolalar-dunyosi", 320_000, 30_000, 10,
     "katta-ayiqcha-150-sm.jpg", "Yumshoq va katta hajmli, ajoyib sovg'a bo'ladigan ayiqcha."),
    ("lego-city-konstruktori", "LEGO City konstruktori", "bolalar-dunyosi", 450_000, 20_000, 16,
     "lego-city-konstruktori.jpg", "Bolalar ijodkorligini rivojlantiruvchi qiziqarli konstruktor."),
    ("pultli-oyinchoq-mashina", "Pultli o'yinchoq mashina", "bolalar-dunyosi", 210_000, 20_000, 22,
     "pultli-oyinchoq-mashina.jpg", "Tezyurar va boshqarish qulay bo'lgan pultli mashina."),

    ("boks-qopi-30kg", "Boks qopi 30kg", "sport-va-dam-olish", 890_000, 40_000, 8,
     "boks-qopi-30kg.jpg", "Uy sharoitida mashq qilish uchun mustahkam boks qopi."),
    ("gantel-10kg-1-juft", "Gantel 10kg (1 juft)", "sport-va-dam-olish", 420_000, 25_000, 16,
     "gantel-10kg-1-juft.jpg", "Kuch mashqlari uchun bardoshli metall gantellar."),
    ("sayohat-chodiri-4-kishilik", "Sayohat chodiri (4 kishilik)", "sport-va-dam-olish", 780_000, 30_000, 10,
     "sayohat-chodiri-4-kishilik.jpg", "Suv o'tkazmaydigan, tez o'rnatiladigan sayohat chodiri."),
    ("trinx-velosipedi", "Trinx tog' velosipedi", "sport-va-dam-olish", 3_200_000, 50_000, 7,
     "trinx-velosipedi.jpg", "Tog'li yo'llarga mos, mustahkam ramkali velosiped."),
    ("yugurish-yolakchasi", "Yugurish yo'lakchasi (trenajor)", "sport-va-dam-olish", 6_500_000, 80_000, 3,
     "yugurish-yolakchasi.jpg", "Uy sharoitida mashq qilish uchun elektr trenajor."),

    ("bogdorchilik-shlangi-20m", "Bog'dorchilik shlangi 20m", "uy-va-bog", 165_000, 20_000, 20,
     "bogdorchilik-shlangi-20m.jpg", "Cho'zilib-torayadigan, ishlatishga qulay bog' shlangi."),
    ("gul-tuvaklari-toplami", "Gul tuvaklari to'plami", "uy-va-bog", 95_000, 20_000, 25,
     "gul-tuvaklari-toplami.jpg", "Turli o'lchamdagi keramik gul tuvaklari to'plami."),
    ("katta-kochma-mangal", "Ko'chma mangal", "uy-va-bog", 340_000, 30_000, 12,
     "katta-kochma-mangal.jpg", "Piknik va tabiatga chiqishlar uchun qulay ko'chma mangal."),
    ("maysazor-oradigan-uskuna", "Maysazor o'radigan uskuna", "uy-va-bog", 2_850_000, 50_000, 5,
     "maysazor-oradigan-uskuna.jpg", "Hovli va bog' uchun quvvatli gazonokosilka."),

    ("kompyuter-stoli", "Kompyuter stoli", "mebel", 890_000, 40_000, 10,
     "kompyuter-stoli.jpg", "Ish va o'qish uchun qulay, zamonaviy dizaynli stol."),
    ("oshxona-stoli-6-kishilik", "Oshxona stoli (6 kishilik)", "mebel", 2_100_000, 50_000, 6,
     "oshxona-stoli-6-kishilik.jpg", "Katta oilalar uchun mos, mustahkam oshxona stoli."),
    ("raxbar-ofis-kreslosi", "Rahbar ofis kreslosi", "mebel", 1_350_000, 40_000, 8,
     "raxbar-ofis-kreslosi.jpg", "Qulay va bardoshli, uzoq ishlash uchun mos kreslo."),
    ("yumshoq-burchak-divani", "Yumshoq burchak divani", "mebel", 4_500_000, 60_000, 4,
     "yumshoq-burchak-divani.jpg", "Mehmonxona uchun katta va qulay burchak divani."),

    ("casio-g-shock-erklar-soati", "Casio G-Shock erkaklar soati", "zargarlik-va-soatlar", 980_000, 20_000, 14,
     "casio-g-shock-erklar-soati.jpg", "Zarbaga chidamli, sport uslubidagi erkaklar soati."),
    ("kumush-zanjir-925-proba", "Kumush zanjir 925 proba", "zargarlik-va-soatlar", 650_000, 20_000, 16,
     "kumush-zanjir-925-proba.jpg", "Yuqori sifatli 925 proba kumushdan tayyorlangan zanjir."),
    ("tilla-uzuk-585-proba", "Tilla uzuk 585 proba", "zargarlik-va-soatlar", 3_200_000, 25_000, 6,
     "tilla-uzuk-585-proba.jpg", "Nafis dizaynli, 585 proba oltindan yasalgan uzuk."),
    ("tissot-klassik-soati", "Tissot klassik soati", "zargarlik-va-soatlar", 4_800_000, 25_000, 5,
     "tissot-klassik-soati.jpg", "Shveytsariya ishlab chiqarishi klassik qo'l soati."),
]


class Command(BaseCommand):
    help = "Kategoriya va mahsulotlarni media/ papkasidagi mavjud rasmlar bilan to'ldiradi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Ishga tushirishdan oldin mavjud kategoriya va mahsulotlarni o'chiradi.",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            Product.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(self.style.WARNING("Mavjud kategoriya va mahsulotlar o'chirildi."))

        categories = {}
        for cat in CATEGORIES:
            obj, created = Category.objects.update_or_create(
                slug=cat["slug"],
                defaults={"title": cat["title"], "image": f"categories/{cat['icon']}"},
            )
            categories[cat["slug"]] = obj
            self.stdout.write(f"{'+ Yaratildi' if created else '~ Yangilandi'}: {obj.title}")

        created_count = 0
        updated_count = 0
        for slug, title, cat_slug, price, delivery_price, stock, image, description in PRODUCTS:
            obj, created = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "category": categories[cat_slug],
                    "price": price,
                    "delivery_price": delivery_price,
                    "stock_quantity": stock,
                    "image": f"products/{image}",
                    "description": description,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Tayyor: {len(categories)} kategoriya, {created_count} yangi mahsulot, "
            f"{updated_count} yangilangan mahsulot."
        ))
