import sqlite3

from hb_store_m1.main import init_db
from hb_store_m1.models.globals import Globals
from hb_store_m1.models.output import Output, Status
from hb_store_m1.models.pkg.pkg import PKG


def insert(pkgs: list[PKG]) -> Output:

    store_db_file_path = Globals.FILES.STORE_DB_FILE_PATH
    if not store_db_file_path.exists():
        init_db()

    if not store_db_file_path.exists():
        return Output(Status.ERROR, f"store.db not found at {store_db_file_path}")

    if not pkgs:
        return Output(Status.SKIP, 0)

    conn = sqlite3.connect(str(store_db_file_path))

    # TODO IMPLEMENTAR SINGLE E BATCH
    try:
        conn.execute("BEGIN")

        insert_sql = """
                     INSERT INTO homebrews (id, name, "desc", image, package, version, picpath, desc_1, desc_2,
                                            ReviewStars, Size, Author, apptype, pv, main_icon_path, main_menu_pic,
                                            releaseddate, number_of_downloads, github, video, twitter, md5)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                     ON CONFLICT(version, id) DO UPDATE SET
                        name=excluded.name,
                        "desc"=excluded."desc",
                        image=excluded.image,
                        package=excluded.package,
                        picpath=excluded.picpath,
                        desc_1=excluded.desc_1,
                        desc_2=excluded.desc_2,
                        ReviewStars=excluded.ReviewStars,
                        Size=excluded.Size,
                        Author=excluded.Author,
                        apptype=excluded.apptype,
                        pv=excluded.pv,
                        main_icon_path=excluded.main_icon_path,
                        main_menu_pic=excluded.main_menu_pic,
                        releaseddate=excluded.releaseddate,
                        number_of_downloads=excluded.number_of_downloads,
                        github=excluded.github,
                        video=excluded.video,
                        twitter=excluded.twitter,
                        md5=excluded.md5
                     """
        (
            id,
            name,
            "desc",
            image,
            package,
            version,
            picpath,
            desc_1,
            desc_2,
            ReviewStars,
            Size,
            Author,
            apptype,
            pv,
            main_icon_path,
            main_menu_pic,
            releaseddate,
            number_of_downloads,
            github,
            video,
            twitter,
            md5,
        )
        rows_to_insert = []
        for pkg in pkgs:
            rows_to_insert.append(
                (
                    pkg.title_id,
                    pkg.title,
                    "",  # description
                    pkg.icon0_png_path,
                    pkg.pkg_path,
                    pkg.version,
                    "",  # picpath
                    "",  # desc1
                    "",  # desc2
                    None,  # float
                    pkg.pkg_path.__sizeof__(),  # size ?
                    "",
                    app_type,
                    "",
                    icon_path,
                    menu_pic_path,
                    pkg.release_date or "",
                    0,
                    "",
                    "",
                    "",
                    "",
                )
            )
            icon_path = str(pkg.icon0_png_path) if pkg.icon0_png_path else ""
            menu_pic_path = ""
            if pkg.pic1_png_path:
                menu_pic_path = str(pkg.pic1_png_path)
            elif pkg.pic0_png_path:
                menu_pic_path = str(pkg.pic0_png_path)

            app_type = pkg.app_type.value if pkg.app_type else ""

        if rows_to_insert:
            conn.executemany(insert_sql, rows_to_insert)

        conn.commit()
        return Output(Status.OK, len(rows_to_insert))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
