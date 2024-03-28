import { useState, useRef } from "react";
import axios from "axios";
import styles from "./vc_train_upload.module.css";
import { MdCloudUpload, MdDelete } from "react-icons/md";
import { AiFillFileImage } from "react-icons/ai";

const VC_Train_Upload = () => {
  const [fileNames, setFileNames] = useState([]);
  const [files, setFiles] = useState([]);
  const formRef = useRef(null);

  const handleFilesChange = ({ target: { files } }) => {
    setFiles(files);
    const fileNamesArray = Array.from(files).map((file) => file.name);
    setFileNames(fileNamesArray);
  };

  const deleteFile = (index) => {
    const newFileNames = [...fileNames];
    const newFiles = [...files];
    newFileNames.splice(index, 1);
    newFiles.splice(index, 1);
    setFileNames(newFileNames);
    setFiles(newFiles);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const formData = new FormData();
    formData.append("user_id", "111");
    formData.append("artist", "lee");
    Array.from(files).forEach((file) => {
      formData.append("files", file);
    });

    try {
      const response = await axios.post(
        "http://localhost:5000/vc_training",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );
      console.log("Server Response:", response.data);
    } catch (error) {
      console.error("Error uploading files:", error);
    }
  };

  const handleExternalSubmit = () => {
    if (formRef.current) {
      formRef.current.dispatchEvent(
        new Event("submit", { cancelable: true, bubbles: true })
      );
    }
  };

  return (
    <main className={styles.mainContainer}>
      <form ref={formRef} onSubmit={handleSubmit} className={styles.formStyle}>
        <input
          type="file"
          accept="audio/*"
          className="input-field"
          hidden
          multiple
          onChange={handleFilesChange}
        />
        <div
          className={styles.uploadArea}
          onClick={() => document.querySelector(".input-field").click()}
        >
          {fileNames.length === 0 ? (
            <>
              <MdCloudUpload color="#1475cf" size={70} />
              <p>Train 할 파일들을 업로드하세요</p>
            </>
          ) : (
            <h2 className={styles.Text}>{fileNames.length} file(s) selected</h2>
          )}
        </div>
      </form>
      {fileNames.length > 0 && (
        <section className={styles.uploadedRow}>
          <AiFillFileImage color="#1475cf" size={40} />
          <span className={styles.Text}>
            {fileNames.slice(0, 2).join(", ") +
              (fileNames.length > 2 ? ", ..." : "")}
            <MdDelete onClick={deleteFile} />
          </span>
        </section>
      )}
      <button className={styles.submitButton} onClick={handleExternalSubmit}>
        Upload Files
      </button>
    </main>
  );
};

export default VC_Train_Upload;
