databases = [
    {
        "id": "2848a998-e151-4d5a-9813-0904a44c2397",
        "name": "db-postgresql-fra1-82725",
        "engine": "pg",
        "version": "14",
        "connection": {
            "protocol": "postgresql",
            "uri": "postgresql://doadmin:password@host.b.db.ondigitalocean.com:25060/defaultdb?sslmode=require",
            "database": "defaultdb",
            "host": "host.b.db.ondigitalocean.com",
            "port": 25060,
            "user": "doadmin",
            "password": "password",
            "ssl": True
        },
        "private_connection": {
            "protocol": "postgresql",
            "uri": "postgresql://doadmin:password@host.b.db.ondigitalocean.com:25060/defaultdb?sslmode=require",
            "database": "defaultdb",
            "host": "host.b.db.ondigitalocean.com",
            "port": 25060,
            "user": "doadmin",
            "password": "password",
            "ssl": True
        },
        "users": [
            {
                "name": "doadmin",
                "role": "primary",
                "password": "password"
            }
        ],
        "db_names": [
            "defaultdb"
        ],
        "num_nodes": 1,
        "region": "fra1",
        "status": "online",
        "created_at": "2022-03-10T11:40:04Z",
        "maintenance_window": {
            "day": "thursday",
            "hour": "21:16:36",
            "pending": False
        },
        "size": "db-s-1vcpu-1gb",
        "tags": None,
        "private_network_uuid": "0d3176ad-41e0-4021-b831-0c5c45c60959"
    }
]
