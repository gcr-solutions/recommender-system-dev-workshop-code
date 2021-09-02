import * as cdk from '@aws-cdk/core';
import * as ec2 from "@aws-cdk/aws-ec2";
import * as iam from '@aws-cdk/aws-iam';
import * as codecommit from '@aws-cdk/aws-codecommit';
import * as ssm from '@aws-cdk/aws-ssm'
import * as path from 'path';
import {
  Asset
} from '@aws-cdk/aws-s3-assets';

import {
  KeyPair
} from 'cdk-ec2-key-pair';


export class RsEC2CdkStack extends cdk.Stack {
  constructor(scope: cdk.Construct, id: string, props ? : cdk.StackProps) {

    super(scope, id, props);

    this.templateOptions.description = "(SO8010) CDK for GCR solution: recommender system"

    // The code that defines your stack goes here
    const namePrefix = 'gcrRsDevWorkshop'
    // Create a Key Pair to be used with this EC2 Instance
    const key = new KeyPair(this, `${namePrefix}KeyPair`, {
      name: `${namePrefix}Keypair`,
      description: 'Key Pair created with CDK Deployment',
    });
    key.grantReadOnPublicKey


    // Create new VPC with 2 Subnets
    const vpc = new ec2.Vpc(this, `${namePrefix}VPC`, {
      natGateways: 1,
      subnetConfiguration: [{
          cidrMask: 24,
          name: `${namePrefix}PublicSubnet`,
          subnetType: ec2.SubnetType.PUBLIC,
        },
        {
          cidrMask: 24,
          name: `${namePrefix}PrivateSubnet`,
          subnetType: ec2.SubnetType.PRIVATE
        }
      ]
    });

    const securityGroup = new ec2.SecurityGroup(this, `${namePrefix}Ec2SecurityGroup`, {
      vpc,
      description: 'Allow (TCP port 22, 80, 8081 - 8089) in',
      allowAllOutbound: true
    });

    securityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(80), 'Allow Port 80 Access')
    securityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(22), 'Allow Port 22 (SSH) Access')
    securityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(443), 'Allow Port 443 Access')
    securityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcpRange(8081, 8089), 'Allow 8081 - 8089 Access')

    const role = new iam.Role(this, `${namePrefix}Ec2Role`, {
      assumedBy: new iam.ServicePrincipal(`ec2.${this.urlSuffix}`)
    })

    role.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AdministratorAccess'))

    const ami = new ec2.AmazonLinuxImage({
      generation: ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
      cpuType: ec2.AmazonLinuxCpuType.X86_64
    });

    const repo = new codecommit.Repository(this, `${namePrefix}Repository`, {
      repositoryName: `${namePrefix}Repo`,
      description: 'CodeCommit Repository'
    });


    const rootVolume: ec2.BlockDevice = {
      deviceName: '/dev/xvda',
      volume: ec2.BlockDeviceVolume.ebs(100, {
        deleteOnTermination: true
      }),
    };

    const ec2Instance = new ec2.Instance(this, `${namePrefix}Ec2Instance`, {
      vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T2, ec2.InstanceSize.XLARGE),
      machineImage: ami,
      securityGroup: securityGroup,
      keyName: key.keyPairName,
      role: role,
      blockDevices: [rootVolume]
    });

    repo.grantPullPush(ec2Instance)
    ec2Instance.node.addDependency(repo)

    // const userDataScript = readFileSync(path.join(__dirname, './config/ec2-user-data.sh'), 'utf8');
    // ec2Instance.addUserData(userDataScript)

    const asset = new Asset(this, 'Asset', {
      path: path.join(__dirname, './config/ec2-user-data.sh')
    });
    asset.grantRead(ec2Instance.role);
    const localPath = ec2Instance.userData.addS3DownloadCommand({
      bucket: asset.bucket,
      bucketKey: asset.s3ObjectKey,
    });
    ec2Instance.userData.addExecuteFileCommand({
      filePath: localPath,
      arguments: repo.repositoryCloneUrlHttp
    });

    new ssm.StringParameter(this, `${namePrefix}VpcId`, {
      stringValue: vpc.vpcId,
      parameterName: `${namePrefix}VpcId`
    });

    new ssm.StringParameter(this, `${namePrefix}PublicSubnets`, {
      stringValue: vpc.publicSubnets.map(s => s.subnetId).join(","),
      parameterName: `${namePrefix}PublicSubnets`
    });

    new ssm.StringParameter(this, `${namePrefix}PrivateSubnets`, {
      stringValue: vpc.privateSubnets.map(s => s.subnetId).join(","),
      parameterName: `${namePrefix}PrivateSubnets`
    });


    new cdk.CfnOutput(this, 'VPC ID', {
      value: vpc.vpcId
    });

    new cdk.CfnOutput(this, 'Public Subnets', {
      value: vpc.publicSubnets.map(s => s.subnetId).join(",")
    });

    new cdk.CfnOutput(this, 'Private Subnets', {
      value: vpc.privateSubnets.map(s => s.subnetId).join(",")
    });

    new cdk.CfnOutput(this, 'Key Name', {
      value: key.keyPairName
    })
    new cdk.CfnOutput(this, 'Download Key Command', {
      value: `aws secretsmanager get-secret-value --secret-id ec2-ssh-key/${key.keyPairName}/private --query SecretString --output text > rs-ec2-key.pem && chmod 400 rs-ec2-key.pem`
    })
    new cdk.CfnOutput(this, 'SSH Command', {
      value: 'ssh -i rs-ec2-key.pem -o IdentitiesOnly=yes ec2-user@' + ec2Instance.instancePublicIp
    })
    new cdk.CfnOutput(this, 'Http URL', {
      value: 'http://' + ec2Instance.instancePublicIp
    })
  }
}