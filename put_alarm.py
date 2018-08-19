#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import boto3
import configparser

BASE_DIRPATH = os.path.dirname(os.path.abspath(__file__))

# アラームを作成する際のパラメータのテンプレートを設定しているファイル
PUT_ALARM_TEMPLATE = \
    os.path.join(BASE_DIRPATH, "conf", "put-alarm-template.conf")

# アラーム削除の際の名前のパターンを記述するファイル
DELETE_ALARM_PATURN_FILE = \
    os.path.join(BASE_DIRPATH, "conf", "delete-list.conf")


def get_instance_name(instance):
    name_tag = [x['Value'] for x in instance.tags if x['section'] == 'Name']
    name = name_tag[0] if len(name_tag) else ''
    return name


def delete_alarms():
    deleteAlarmNames = []
    deletePatterns = []

    # 設定ファイルより、削除対象のアラーム名のパターンのリスト取得を作成
    with open(DELETE_ALARM_PATURN_FILE) as f:
        for line in f:
            deletePatterns.append(line.rstrip('\r\n'))

    cw = boto3.client("cloudwatch")
    alarms = cw.describe_alarms()
    for alarm in alarms["MetricAlarms"]:
        # パターン一覧とアラーム名を当てて、一部一致したもの削除対象に
        for pattern in deletePatterns:
            if pattern in alarm["AlarmName"]:
                deleteAlarmNames.append(alarm["AlarmName"])

    cw.delete_alarms(AlarmNames=deleteAlarmNames)


# EC2からデータを抜いてアラームを作成
# configparserを使っているのでテンプレートの形式はそれに合わせる
def put_alarms():
    ec2 = boto3.resource("ec2")
    cw = boto3.client("cloudwatch")

    # 設定ファイルからアラームの設定一覧項目を取得
    config = configparser.ConfigParser()
    config.read(PUT_ALARM_TEMPLATE)

    # ec2インスタンス情報を取得
    instances = ec2.instances.all()
    for i in instances:
        for section in config.sections():

            # target の部分がインスタンス対象のインスタンス一覧となっている
            if not get_instance_name(i) in config[section]["target"]:
                continue

            # アラーム設定
            ip = i.private_ip_address
            cw.put_metric_alarm(
                AlarmName=config[section]["AlarmName"].format(local_ip=ip),
                Namespace=config[section]["Namespace"],
                MetricName=config[section]["MetricName"].format(local_ip=ip),
                ComparisonOperator=config[section]["ComparisonOperator"],
                AlarmActions=config[section]["AlarmActions"].split(","),
                Threshold=float(config[section]["Threshold"]),
                Period=int(config[section]["Period"]),
                EvaluationPeriods=int(config[section]["EvaluationPeriods"]),
                Statistic=config[section]["Statistic"]
            )


if __name__ == "__main__":
    delete_alarms()
    put_alarms()
