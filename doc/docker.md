### Docker

#### Install Docker(安装Docker)

```
sudo apt install -y docker docker.io docker-registry
```

#### Build Image yourself(自行创建镜像)
```
cd /path/to/SUSTech

# Build docker image (构建镜像)

sudo docker build -f Docker/Dockerfile -t sustechpoints:latest .

# Create container of server (创建容器)
# Python base image is 3.10, consistent with the local environment.
# Replace ${YourDataPath} with your dataset path.
# The container serves HTTP on port 8092 through uWSGI.

sudo docker run -d --restart=always \
  --name sustechpoints \
  -p 8092:8092 \
  -v ${YourDataPath}:/app/data \
  sustechpoints:latest

```

Server example:

```bash
sudo docker run -d --restart=always \
  --name sustechpoints \
  -p 8092:8092 \
  -v /nvme/label_data/data:/app/data \
  sustechpoints:latest
```

Optional environment variables:

```bash
-e UWSGI_HTTP=0.0.0.0:8092
-e UWSGI_PROCESSES=4
-e UWSGI_THREADS=2
```

#### Use docker image of dockerhub(使用现有镜像, 不保证代码为最新)

```
sudo docker run -d --restart=always -p 8092:8092 juhaoming/sustechpoints:v1.0.0

sudo docker run -d --restart=always \
  -p 8092:8092 \
  -v ${YourDataPath}:/app/data \
  juhaoming/sustechpoints:v1.0.0

```
