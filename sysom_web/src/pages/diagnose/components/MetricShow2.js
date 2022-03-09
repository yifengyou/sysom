import { Button, Statistic } from 'antd';
import { useModel } from 'umi';
import ProCard from '@ant-design/pro-card';
import { Line } from '@ant-design/charts';

const MetricShow = (props) => {
  const { count, handleCount } = useModel('diagnose', model => (
    { 
      count: model.count, 
      handleCount: model.handleCount,
    }
  ))
  const config = {
    data: props.data[count],
    padding: 'auto',
    xField: props.xField,
    yField: props.yField,
    seriesField: props.category,
    xAxis: {
      tickCount: 5,
    },
    slider: {
      start: 0,
      end: 1.0,
    },
  };
  return (
    <>
      <ProCard title={props.title}>
        <Line {...config} />
      </ProCard>
    </>
  );
}
export default MetricShow