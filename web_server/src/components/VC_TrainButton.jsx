import React, { useState } from "react";
import { PoweroffOutlined } from "@ant-design/icons";
import { Button, Flex } from "antd";
import styles from "./vc_trainbutton.module.css";
import axios from "axios";

const VC_TrainButton = () => {
  const [trainStatus, setTrainStatus] = useState("");

  const checkTrainStatus = async () => {
    const requestData = {
      user_id: "111",
      artist: "lee",
    };

    try {
      const response = await axios.post(
        "http://localhost:5000/vc_train_check",
        requestData
      );
      console.log(response.data);
      setTrainStatus(response.data);
    } catch (error) {
      console.error("Error fetching train status:", error);
      setTrainStatus("Failed to fetch train status");
    }
  };

  return (
    <div className={styles.Button}>
      <div className={styles.Text}>
        <h4>Train 하는데 2시간정도의 시간이 걸립니다</h4>
        <h4>Train Status 버튼을 눌러 상태를 확인하세요</h4>
        <h5>Train이 완료되면 Voice conversion을 시도해보세요</h5>
      </div>
      <div className={styles.TrainStatus2}>
        <button className={styles.TrainStatus} onClick={checkTrainStatus}>
          Train 상태 확인
        </button>
      </div>
      {trainStatus && <div className={styles.StatusMessage}>{trainStatus}</div>}
    </div>
  );
};
export default VC_TrainButton;
