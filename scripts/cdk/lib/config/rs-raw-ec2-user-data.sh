set -e

exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
echo "Start time: $(date '-u')"

sudo su
yum update -y

# docker
amazon-linux-extras install docker -y
service docker start
usermod -a -G docker ec2-user

# software
yum install git -y
yum install jq -y


AWS_REGION=$(curl -s 169.254.169.254/latest/dynamic/instance-identity/document | jq -r '.region')
echo AWS_REGION=$AWS_REGION
ACCOUNT_ID=$(aws sts get-caller-identity --region $AWS_REGION --output text --query Account)

# code
echo "==== setup code ======"
export HOME=/home/ec2-user

#https://git-codecommit.ap-northeast-1.amazonaws.com/v1/repos/gcrRsDevWorkshopRepo

url_suffix='com'
if [[ $AWS_REGION =~ ^cn.* ]];then
    url_suffix='com.cn'
fi 
repo_name="https://git-codecommit.$AWS_REGION.amazonaws.${url_suffix}/v1/repos/recommender-system-dev-workshop-code"
echo $repo_name

echo "run git config --global"
git config --global user.name "rs-dev-workshop"
git config --global user.email "rs-dev-workshop@example.com"
git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true
echo "git config --global --list"
git config --global --list
echo ""

if [[ $AWS_REGION =~ ^cn.*]]; then 
    curl -o kubectl https://amazon-eks.s3.cn-north-1.amazonaws.com.cn/1.21.2/2021-07-05/bin/linux/amd64/kubectl
    chmod +x ./kubectl
    mv ./kubectl /usr/local/bin/kubectl

    curl --silent --location "https://aws-gcr-solutions-assets.s3.cn-northwest-1.amazonaws.com.cn/gcr-rs/eks/eksctl_Linux_amd64.tar.gz" | tar xz -C /tmp
    chmod +x /tmp/eksctl
    mv /tmp/eksctl /usr/local/bin

else
    curl -LO https://storage.googleapis.com/kubernetes-release/release/`curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt`/bin/linux/amd64/kubectl
    chmod +x ./kubectl
    mv ./kubectl /usr/local/bin/kubectl

    UNAME=$(uname -s)
    curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_${UNAME}_amd64.tar.gz" | tar xz -C /tmp
    chmod +x /tmp/eksctl
    mv /tmp/eksctl /usr/local/bin

fi 

eksctl version
kubectl version --client

echo "==== config AWS ENV ======"
# config AWS ENV
sudo -u ec2-user -i <<EOS
echo "set default.region"
aws configure set default.region ${AWS_REGION}
aws configure get default.region
echo "export ACCOUNT_ID=${ACCOUNT_ID}" | tee -a /home/ec2-user/.bash_profile
echo "export AWS_REGION=${AWS_REGION}" | tee -a /home/ec2-user/.bash_profile
echo "export REGION=${AWS_REGION}" | tee -a /home/ec2-user/.bash_profile

mkdir /home/ec2-user/environment
cd /home/ec2-user/environment
#wget https://github.com/gcr-solutions/recommender-system-dev-workshop-code/archive/refs/heads/main.zip
wget https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/rs-dev-workshop-code/latest/main.zip
unzip main.zip

echo "git clone ${repo_name}"
git clone ${repo_name}

mv ./recommender-system-dev-workshop-code-main/* ./recommender-system-dev-workshop-code/

rm -rf recommender-system-dev-workshop-code-main
cd ./recommender-system-dev-workshop-code/
git add . && git commit -m 'first commit' && git push


EOS

# httpd
yum install -y httpd
systemctl start httpd
systemctl enable httpd

echo "<h1>Hello World from AWS EC2 $(hostname -f)</h1><br><hr><h2>Start Time: $(date -'u' )</h2>" > /var/www/html/index.html

echo "End time: $(date '-u')"
exit 0
