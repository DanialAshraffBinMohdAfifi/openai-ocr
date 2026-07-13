function OcrTextBox({ warnings }) {
  if (!warnings.length) {
    return null;
  }

  return (
    <div className="warning-box">
      <strong>Validation warnings</strong>
      <ul>
        {warnings.map((warning, index) => (
          <li key={`${warning}-${index}`}>{warning}</li>
        ))}
      </ul>
    </div>
  );
}

export default OcrTextBox;
