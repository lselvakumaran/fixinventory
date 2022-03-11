load_balancers = [
    {
        "id": "9625f517-75f0-4af8-a336-62374e68dc0d",
        "name": "fra1-load-balancer-01",
        "ip": "127.0.0.1",
        "size": "lb-small",
        "size_unit": 1,
        "algorithm": "round_robin",
        "status": "new",
        "created_at": "2022-03-10T16:23:10Z",
        "forwarding_rules": [
            {
                "entry_protocol": "http",
                "entry_port": 80,
                "target_protocol": "http",
                "target_port": 80,
                "certificate_id": "",
                "tls_passthrough": False,
            }
        ],
        "health_check": {
            "protocol": "http",
            "port": 80,
            "path": "/",
            "check_interval_seconds": 10,
            "response_timeout_seconds": 5,
            "healthy_threshold": 5,
            "unhealthy_threshold": 3,
        },
        "sticky_sessions": {"type": "none"},
        "region": {
            "name": "Frankfurt 1",
            "slug": "fra1",
            "features": [
                "backups",
                "ipv6",
                "metadata",
                "install_agent",
                "storage",
                "image_transfer",
            ],
            "available": True,
            "sizes": [
                "s-1vcpu-1gb",
                "s-1vcpu-1gb-amd",
                "s-1vcpu-1gb-intel",
                "s-1vcpu-2gb",
                "s-1vcpu-2gb-amd",
                "s-1vcpu-2gb-intel",
                "s-2vcpu-2gb",
                "s-2vcpu-2gb-amd",
                "s-2vcpu-2gb-intel",
                "s-2vcpu-4gb",
                "s-2vcpu-4gb-amd",
                "s-2vcpu-4gb-intel",
                "s-4vcpu-8gb",
                "c-2",
                "c2-2vcpu-4gb",
                "s-4vcpu-8gb-amd",
                "s-4vcpu-8gb-intel",
                "g-2vcpu-8gb",
                "gd-2vcpu-8gb",
                "s-8vcpu-16gb",
                "m-2vcpu-16gb",
                "c-4",
                "c2-4vcpu-8gb",
                "s-8vcpu-16gb-amd",
                "s-8vcpu-16gb-intel",
                "m3-2vcpu-16gb",
                "g-4vcpu-16gb",
                "so-2vcpu-16gb",
                "m6-2vcpu-16gb",
                "gd-4vcpu-16gb",
                "so1_5-2vcpu-16gb",
                "m-4vcpu-32gb",
                "c-8",
                "c2-8vcpu-16gb",
                "m3-4vcpu-32gb",
                "g-8vcpu-32gb",
                "so-4vcpu-32gb",
                "m6-4vcpu-32gb",
                "gd-8vcpu-32gb",
                "so1_5-4vcpu-32gb",
                "m-8vcpu-64gb",
                "c-16",
                "c2-16vcpu-32gb",
                "m3-8vcpu-64gb",
                "g-16vcpu-64gb",
                "so-8vcpu-64gb",
                "m6-8vcpu-64gb",
                "gd-16vcpu-64gb",
                "so1_5-8vcpu-64gb",
                "m-16vcpu-128gb",
                "c-32",
                "c2-32vcpu-64gb",
                "m3-16vcpu-128gb",
                "m-24vcpu-192gb",
                "g-32vcpu-128gb",
                "so-16vcpu-128gb",
                "m6-16vcpu-128gb",
                "gd-32vcpu-128gb",
                "m3-24vcpu-192gb",
                "g-40vcpu-160gb",
                "so1_5-16vcpu-128gb",
                "m-32vcpu-256gb",
                "gd-40vcpu-160gb",
                "so-24vcpu-192gb",
                "m6-24vcpu-192gb",
                "m3-32vcpu-256gb",
                "so1_5-24vcpu-192gb",
                "so-32vcpu-256gb",
                "m6-32vcpu-256gb",
                "so1_5-32vcpu-256gb",
            ],
        },
        "tag": "",
        "droplet_ids": [289110074],
        "redirect_http_to_https": False,
        "enable_proxy_protocol": False,
        "enable_backend_keepalive": False,
        "vpc_uuid": "0d3176ad-41e0-4021-b831-0c5c45c60959",
        "disable_lets_encrypt_dns_records": False,
    }
]
