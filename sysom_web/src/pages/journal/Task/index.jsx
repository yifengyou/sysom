import {  useRef } from 'react';
import { useIntl, FormattedMessage } from 'umi';
import { PageContainer } from '@ant-design/pro-layout';
import ProTable from '@ant-design/pro-table';
import {  getTaskList } from '../service';

const TaskList = () => {
  const actionRef = useRef();
  const intl = useIntl();

  const columns = [
    {
      title: <FormattedMessage id="pages.journal.audit.created_at" defaultMessage="created_at" />,
      dataIndex: 'created_at',
      valueType: 'dateTime',
      hideInSearch: true,
    },
    {
      title: <FormattedMessage id="pages.journal.task.task_id" defaultMessage="task_id" />,
      dataIndex: 'task_id',
      valueType: 'textarea',
    },
    {
      title: <FormattedMessage id="pages.journal.task.status" defaultMessage="status" />,
      dataIndex: 'status',
      valueEnum: {
        "Success": {
          text: (
            <FormattedMessage id="pages.journal.task.success" defaultMessage="Success" />
          ),
          status: 'Success',
        },
        "Fail": {
          text: (
            <FormattedMessage id="pages.journal.task.fail" defaultMessage="Fail" />
          ),
          status: 'Error',
        },
      },
    },
    {
      title: <FormattedMessage id="pages.journal.task.params" defaultMessage="params" />,
      dataIndex: 'params',
      valueType: 'textarea',
      hideInSearch: true
    },
  ];
  return (
    <PageContainer>
      <ProTable
        headerTitle={intl.formatMessage({
          id: 'pages.journal.audit.title',
          defaultMessage: 'Audit',
        })}
        actionRef={actionRef}
        rowKey="id"
        search={{
          labelWidth: 120,
        }}
        toolBarRender={() => [
        ]}
        request={getTaskList}
        columns={columns}
      />
    </PageContainer>
  );
};

export default TaskList;
