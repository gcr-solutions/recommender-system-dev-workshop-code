#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from '@aws-cdk/core';
import { RsRawEC2CdkStack } from '../lib/rs-raw-ec2-cdk-stack';

const app = new cdk.App();
new RsRawEC2CdkStack(app, 'RsRawEC2CdkStack', {});


