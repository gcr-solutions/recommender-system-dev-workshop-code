#!/bin/bash

set -e

repo_name=$1

exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

sudo su
yum update -y

echo "repo_name:$repo_name"

export HOME=/home/ec2-user

# docker
amazon-linux-extras install docker -y
service docker start
usermod -a -G docker ec2-user

# git
yum install git -y
amazon-linux-extras install python3.8 -y


# httpd
yum install -y httpd

systemctl start httpd
systemctl enable httpd

echo "<h1>Hello World from $(hostname -f)</h1><br><h2>Start Time: $(date -'u' )</h2>" > /var/www/html/index.html

# code
mkdir ${HOME}/code
cd ${HOME}/code
wget https://github.com/gcr-solutions/recommender-system-dev-workshop-code/archive/refs/heads/main.zip
unzip main.zip

echo "run git config --global"
git config --global user.name "rs-dev-workshop"
git config --global user.email "rs-dev-workshop@example.com"
git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true
echo "git config --global --list"
git config --global --list
echo ""
echo "git clone ${repo_name}"
git clone ${repo_name}

mv ./recommender-system-dev-workshop-code-main/* ./gcrRsDevWorkshopRepo/
chown -R ec2-user ${HOME}/code

rm -r recommender-system-dev-workshop-code-main
cd ./gcrRsDevWorkshopRepo/
git add . && git commit -m 'first commit' && git push

echo "all done"

