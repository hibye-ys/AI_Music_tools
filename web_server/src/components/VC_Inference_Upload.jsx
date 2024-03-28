import styles from "./vc_inference_upload.module.css";
import { useState, useRef } from "react";
import axios from "axios";
import { MdCloudUpload, MdDelete } from "react-icons/md";
import { AiFillFileImage } from "react-icons/ai";

const VC_Inference_Upload = () => {
  const [fileName, setFileName] = useState("");
  const [file, setFile] = useState(null);
  const formRef = useRef(null);

  const handleFilesChange = ({ target: { files } }) => {
    if (files.length > 0) {
      setFile(files[0]);
      setFileName(files[0].name);
    }
  };

  const deleteFile = () => {
    setFileName("");
    setFile(null);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const formData = new FormData();
    formData.append("artist", "lee");
    formData.append("user_id", "111");
    if (file) {
      formData.append("audio", file);
    }

    try {
      const response = await axios.post(
        "http://localhost:5000/vc_inference",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );
      console.log("Server Response from vc_inference:", response.data);
    } catch (error) {
      console.error("Error uploading file to vc_inference:", error);
    }

    const formData2 = formData;
    formData2.append("vc", true);
    try {
      const response = await axios.post(
        "http://localhost:5000/separate",
        formData2,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );
      console.log("Server Response from separate:", response.data);
    } catch (error) {
      console.error("Error uploading file to separate:", error);
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
          onChange={handleFilesChange}
        />
        <div
          className={styles.uploadArea}
          onClick={() => document.querySelector(".input-field").click()}
        >
          {fileName === "" ? (
            <>
              <MdCloudUpload color="#1475cf" size={70} />
              <p>변환 하고 싶은 파일을 업로드 하세요</p>
            </>
          ) : (
            <h2 className={styles.Text}>{fileName} selected</h2>
          )}
        </div>
      </form>
      {fileName && (
        <section className={styles.uploadedRow}>
          <AiFillFileImage color="#1475cf" size={40} />
          <span className={styles.Text}>
            {fileName}
            <MdDelete onClick={deleteFile} />
          </span>
        </section>
      )}
      <button className={styles.submitButton} onClick={handleExternalSubmit}>
        Upload File
      </button>
    </main>
  );
};

export default VC_Inference_Upload;
