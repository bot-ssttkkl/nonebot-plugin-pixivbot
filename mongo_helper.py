import getpass

from pymongo import MongoClient


def main():
    hostname = input("MongoDB Hostname (Default: localhost): ")
    if not hostname:
        hostname = "localhost"

    port = input("MongoDB Port (Default: 27017): ")
    if not port:
        port = "27017"

    username = input("MongoDB Username: ")
    password = getpass.getpass("MongoDB Password: ")
    database_name = input("MongoDB Database Name: ")

    url = f"mongodb://{username}:{password}@{hostname}:{port}"
    client = MongoClient(url)
    db = client[database_name]

    option = input("1: Create Indexes\n"
                   "2: Drop TTL Indexes\n"
                   "3: Drop Common Indexes\n"
                   "4: Drop Database\n"
                   "Option: ")

    if option == "1":
        db['download_cache'].create_index([("illust_id", 1)], unique=True)
        db['illust_detail_cache'].create_index([("illust.id", 1)], unique=True)
        db['illust_ranking_cache'].create_index([("mode", 1)], unique=True)
        db['search_illust_cache'].create_index([("word", 1)], unique=True)
        db['search_user_cache'].create_index([("word", 1)], unique=True)
        db['user_illusts_cache'].create_index([("user_id", 1)], unique=True)
        db['other_cache'].create_index([("type", 1)], unique=True)

        create_ttl_indexes = input("Create TTL Indexes? [y/N] ")
        if create_ttl_indexes == 'y' or create_ttl_indexes == 'Y':
            download_cache_expires_in = int(input("Download cache expires in (sec): "))
            db['download_cache'].create_index([("update_time", 1)], expireAfterSeconds=download_cache_expires_in)

            illust_detail_cache_expires_in = int(input("Illust detail cache expires in (sec): "))
            db['illust_detail_cache'].create_index([("update_time", 1)],
                                                   expireAfterSeconds=illust_detail_cache_expires_in)

            illust_ranking_cache_expires_in = int(input("Illust ranking cache expires in (sec): "))
            db['illust_ranking_cache'].create_index([("update_time", 1)],
                                                    expireAfterSeconds=illust_ranking_cache_expires_in)

            search_illust_cache_expires_in = int(input("Search illust cache expires in (sec): "))
            db['search_illust_cache'].create_index([("update_time", 1)],
                                                   expireAfterSeconds=search_illust_cache_expires_in)

            search_user_cache_expires_in = int(input("Search user cache expires in (sec): "))
            db['search_user_cache'].create_index([("update_time", 1)], expireAfterSeconds=search_user_cache_expires_in)

            user_illusts_cache_expires_in = int(input("User illusts cache expires in (sec): "))
            db['user_illusts_cache'].create_index([("update_time", 1)],
                                                  expireAfterSeconds=user_illusts_cache_expires_in)

            other_cache_expires_in = int(input("User bookmarks and recommended illusts cache expire in (sec): "))
            db['other_cache'].create_index([("update_time", 1)], expireAfterSeconds=other_cache_expires_in)
    elif option == "2":
        db['download_cache'].drop_index([("update_time", 1)])
        db['illust_detail_cache'].drop_index([("update_time", 1)])
        db['illust_ranking_cache'].drop_index([("update_time", 1)])
        db['search_illust_cache'].drop_index([("update_time", 1)])
        db['search_user_cache'].drop_index([("update_time", 1)])
        db['user_illusts_cache'].drop_index([("update_time", 1)])
        db['other_cache'].drop_index([("update_time", 1)])
    elif option == "3":
        db['download_cache'].drop_index([("illust_id", 1)])
        db['illust_detail_cache'].drop_index([("illust_id", 1)])
        db['illust_ranking_cache'].drop_index([("mode", 1)])
        db['search_illust_cache'].drop_index([("word", 1)])
        db['search_user_cache'].drop_index([("word", 1)])
        db['user_illusts_cache'].drop_index([("user_id", 1)])
        db['other_cache'].drop_index([("type", 1)])
    elif option == "4":
        comfirm = input("Sure? [y/N]")
        if comfirm == 'y' or comfirm == 'Y':
            client.drop_database(database_name)
    else:
        print("Invalid Option.")


if __name__ == '__main__':
    main()
