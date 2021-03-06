function exitTrap(){
 exitCode=$?
 /opt/aws/bin/cfn-signal --stack ${AWS::StackName} --resource __EC2_PHYSICALNAME_ID__ --region ${AWS::Region} -e $exitCode || echo 'Failed to send Cloudformation Signal'
}
trap exitTrap EXIT

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
export HOME=/home/ec2-user

#https://git-codecommit.ap-northeast-1.amazonaws.com/v1/repos/gcrRsDevWorkshopRepo

url_suffix='com'
if [[ $AWS_REGION =~ ^cn.* ]];then
    url_suffix='com.cn'
fi 
repo_name="https://git-codecommit.$AWS_REGION.amazonaws.$url_suffix/v1/repos/recommender-system-dev-workshop-code"
echo $repo_name

echo "run git config --global"
git config --global user.name "rs-dev-workshop"
git config --global user.email "rs-dev-workshop@example.com"
git config --global credential.helper '!aws codecommit credential-helper $@'
git config --global credential.UseHttpPath true
echo "git config --global --list"
git config --global --list
echo ""

if [[ $AWS_REGION =~ ^cn.* ]]; then
    echo "install kubectl and eksctl in $AWS_REGION"
    #curl -o kubectl https://amazon-eks.s3.cn-north-1.amazonaws.com.cn/1.21.2/2021-07-05/bin/linux/amd64/kubectl
    curl -o kubectl https://aws-gcr-solutions-assets.s3.cn-northwest-1.amazonaws.com.cn/gcr-rs/eks/kubectl
    chmod +x ./kubectl
    mv ./kubectl /usr/local/bin/kubectl

    curl --silent --location "https://aws-gcr-solutions-assets.s3.cn-northwest-1.amazonaws.com.cn/gcr-rs/eks/eksctl_Linux_amd64.tar.gz" | tar xz -C /tmp
    chmod +x /tmp/eksctl
    mv /tmp/eksctl /usr/local/bin

else
    echo "install kubectl and eksctl in $AWS_REGION"
    curl -LO https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/eks/kubectl
    chmod +x ./kubectl
    mv ./kubectl /usr/local/bin/kubectl

    curl --silent --location "https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/eks/eksctl_Linux_amd64.tar.gz" | tar xz -C /tmp
    chmod +x /tmp/eksctl
    mv /tmp/eksctl /usr/local/bin

fi 

echo "eksctl version"
eksctl version
echo "kubectl version --client"
kubectl version --client

echo "==== config AWS ENV ======"
# config AWS ENV
sudo -u ec2-user -i <<EOS
echo "set default.region"
aws configure set default.region $AWS_REGION
aws configure get default.region
echo "export ACCOUNT_ID=$ACCOUNT_ID" | tee -a /home/ec2-user/.bash_profile
echo "export AWS_REGION=$AWS_REGION" | tee -a /home/ec2-user/.bash_profile
echo "export REGION=$AWS_REGION" | tee -a /home/ec2-user/.bash_profile

mkdir /home/ec2-user/environment
cd /home/ec2-user/environment
echo "begin downloading code ..."
#wget https://github.com/gcr-solutions/recommender-system-dev-workshop-code/archive/refs/heads/main.zip
wget --quiet https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/rs-dev-workshop-code/latest/main.zip || {
   sleep 5
   curl https://aws-gcr-rs-sol-workshop-ap-northeast-1-common.s3.ap-northeast-1.amazonaws.com/rs-dev-workshop-code/latest/main.zip -o main.zip
}
unzip main.zip

echo "git clone $repo_name"
git clone $repo_name

mv ./recommender-system-dev-workshop-code-main/* ./recommender-system-dev-workshop-code/

rm -rf recommender-system-dev-workshop-code-main
cd ./recommender-system-dev-workshop-code/
git add . && git commit -m 'first commit' && git push

echo "keygen"
ssh-keygen -t rsa -N '' -f /home/ec2-user/.ssh/id_rsa <<< y
aws ec2 delete-key-pair --key-name "gcr-rs-dev-workshop-key" || true
aws ec2 import-key-pair --key-name "gcr-rs-dev-workshop-key" --public-key-material file:///home/ec2-user/.ssh/id_rsa.pub

EOS

# httpd
yum install -y httpd
systemctl start httpd
systemctl enable httpd

echo "<h1>Hello World from AWS EC2 $(hostname -f)</h1><br><hr><h2>Start Time: $(date -'u' )</h2>" > /var/www/html/index.html

echo "End time: $(date '-u')"
exit 0
