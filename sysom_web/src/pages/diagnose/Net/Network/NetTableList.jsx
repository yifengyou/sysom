import React, { useRef } from "react";
import ProTable from "@ant-design/pro-table";
import { getTaskList } from "../../service";
import { Button } from "antd";

function parseJsonString(str) {
  try {
    return JSON.parse(str.replace(/\'/g, "\""));
  }
  catch (e) {
    return {}
  }
}

const getPingTraceList = async () => {
  try {
    let msg = await getTaskList({ service_name: "pingtrace" });
    msg.data = msg.data.map((item) => ({ ...item, ...parseJsonString(item.params) }))
    return {
      data: msg.data.reverse(),
      success: true,
      total: msg.total,
    };
  } catch (e) {
    return { success: false }
  }
}


const DiagnoTableList = React.forwardRef((props, ref) => {


  const columns = [
    {
      title: "源实例IP",
      dataIndex: "源实例IP",
      valueType: "textarea"
    },
    {
      title: "目标实例IP",
      dataIndex: "目标实例IP",
      valueType: "textarea"
    },
    {
      title: "追踪包数",
      dataIndex: "追踪包数",
      valueType: "textarea",
    },
    {
      title: "间隔毫秒数",
      dataIndex: "间隔毫秒数",
      valueType: "textarea",
    },
    {
      title: "报文协议",
      dataIndex: "报文协议",
      valueType: "select",
      valueEnum: {
        icmp: { text: 'ICMP', status: 'icmp' },
        tcp: { text: 'TCP', status: 'tcp' }
      }
    },
    {
      title: "创建时间",
      sortOrder: "descend",
      dataIndex: "created_at",
      valueType: "dateTime",
    },
    {
      title: "PingTraceId",
      dataIndex: "task_id",
      valueType: "textarea",
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 150,
      valueEnum: {
        Running: { text: '运行中', status: 'Processing' },
        Success: { text: '诊断完毕', status: 'Success' },
        Fail: { text: '异常', status: 'Error' },
      },
    },
    {
      title: "操作",
      dataIndex: "option",
      valueType: "option",
      render: (_, record) => {
        if (record.status == "Success") {
          return (
            <a key="showDiagnose" onClick={() => {
              props?.onClick?.(record)
            }}>查看诊断结果</a>
          )
        }
        else if (record.status == "Fail") {
          return (
            <a key="showError" onClick={() => {
              props?.onError?.(record)
            }}>查看出错信息</a>
          )
        }
        else {
          return (<span>暂无可用操作</span>);
        }
      },
    }
  ];

  const pagination=(props.pagination) ? props.pagination: {pageSize: 5}
  return (
    <ProTable
      headerTitle={props.headerTitle}
      actionRef={ref}
      params={props.params}
      rowKey="id"
      request={getPingTraceList}
      columns={columns}
      pagination={pagination}
      search={false}
    />
  );
});

export default DiagnoTableList;
