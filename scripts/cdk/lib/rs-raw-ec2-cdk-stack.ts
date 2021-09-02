import * as cdk from '@aws-cdk/core';
import * as ec2 from "@aws-cdk/aws-ec2";
import * as iam from '@aws-cdk/aws-iam';
import * as path from 'path';
import {readFileSync} from 'fs';

export class RsRawEC2CdkStack extends cdk.Stack {
  constructor(scope: cdk.Construct, id: string, props ? : cdk.StackProps) {

    super(scope, id, props);

    this.templateOptions.description = "(SO8010) CDK for GCR solution: recommender system"
    
    const keyPairParam = new cdk.CfnParameter(this, 'KeyPairParam', {
      type: 'AWS::EC2::KeyPair::KeyName',
      description: "Key Pair to access EC2"
    });

    const namePrefix = 'gcrRsDevWorkshopEc2'

    const vpc = new ec2.Vpc(this, `${namePrefix}VPC`, {
      subnetConfiguration: [{
          cidrMask: 24,
          name: `${namePrefix}PublicSubnet`,
          subnetType: ec2.SubnetType.PUBLIC,
        }
      ]
    });

    const securityGroup = new ec2.SecurityGroup(this, `${namePrefix}Ec2SecurityGroup`, {
      vpc,
      description: 'Allow (TCP port 22, 80) in',
      allowAllOutbound: true
    });

    securityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(80), 'Allow Port 80 Access')
    securityGroup.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(22), 'Allow Port 22 (SSH) Access')

    const role = new iam.Role(this, `${namePrefix}Ec2Role`, {
      assumedBy: new iam.ServicePrincipal(`ec2.${this.urlSuffix}`)
    });

    role.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('PowerUserAccess'))

    const ami = new ec2.AmazonLinuxImage({
      generation: ec2.AmazonLinuxGeneration.AMAZON_LINUX_2,
      cpuType: ec2.AmazonLinuxCpuType.X86_64
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
      keyName: keyPairParam.valueAsString,
      role: role,
      blockDevices: [rootVolume]
    });

    const userDataFile = path.join(__dirname, './config/rs-raw-ec2-user-data.sh')
    const userDataScript = readFileSync(userDataFile, 'utf8');
    ec2Instance.addUserData(userDataScript)

    new cdk.CfnOutput(this, 'SSH Command', {
      value: `ssh -i ${keyPairParam.valueAsString}.pem -o IdentitiesOnly=yes ec2-user@${ec2Instance.instancePublicIp}`  
    });

    new cdk.CfnOutput(this, 'EC2 IP', {
      value: ec2Instance.instancePublicIp
    });
  }
}