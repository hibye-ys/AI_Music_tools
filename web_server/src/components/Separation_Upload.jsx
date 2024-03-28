import React, { useState, useRef } from "react";
import styles from "./separation_upload.module.css";
import axios from "axios";
import Separation_Status from "./Separation_Status"; // 다른 컴포넌트를 임포트합니다.
import Separation_Record from "./Separation_Record";
import { AiOutlineUpload } from "react-icons/ai";

function Separation_Upload() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileName, setFileName] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadComplete, setUploadComplete] = useState(false);

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      setFileName(file.name);
      setSelectedFile(file);
    }
  };

  const handleClick = () => {
    document.getElementById("file_input").click();
  };

  const handleUpload = () => {
    if (!selectedFile) return;

    setUploading(true);
    const formData = new FormData();
    formData.append("user_id", "111");
    formData.append("artist", "lee");
    formData.append("audio", selectedFile);

    axios
      .post("http://localhost:5000/separate", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      })
      .then(() => {
        setUploadComplete(true);
      })
      .catch(() => {
        setUploading(false);
      });
  };

  if (uploadComplete) {
    return (
      <>
        <Separation_Status filename={selectedFile.name} />
        <Separation_Record />
      </>
    );
  }

  return (
    <div>
      {uploading ? (
        <h1 className={styles.Loading}>Loading...</h1>
      ) : (
        <div className={styles.UploadButton}>
          <input
            type="file"
            id="file_input"
            style={{ display: "none" }}
            onChange={handleFileChange}
          />
          <div>
            <button className={styles.customButton} onClick={handleClick}>
              클릭하여 파일을 업로드 하세요
            </button>
          </div>
          <AiOutlineUpload className={styles.upload} onClick={handleUpload} />
        </div>
      )}
    </div>
  );
}

export default Separation_Upload;
