set -e

exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

sudo su
yum update -y

# docker
amazon-linux-extras install docker -y
service docker start
usermod -a -G docker ec2-user

# git
yum install git -y

# httpd
yum install -y httpd

systemctl start httpd
systemctl enable httpd

echo "<h1>Hello World from AWS EC2 $(hostname -f)</h1><br><hr><h2>Start Time: $(date -'u' )</h2>" > /var/www/html/index.html

