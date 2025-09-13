import React, {useRef} from 'react';
import PropTypes from 'prop-types';
import {Tooltip, IconButton} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import * as htmlToImage from 'html-to-image';
import {makeStyles} from '@mui/styles';

const useStyles = makeStyles({
  exportButton: {
    position: 'absolute',
    top: 65,
    right: 10,
    zIndex: 1000,
    backgroundColor: '#fff',
    border: '1px solid #ccc',
    borderRadius: 4,
    boxShadow: '0 1px 4px rgba(0,0,0,0.2)',
    padding: 4,
  },
});

/**
 * Export a DOM node as an image (PNG).
 *
 * @param {HTMLElement} targetNode - The DOM element to export.
 * @param {string} fileName - Name of the downloaded file.
 * @param {Function} [beforeExport] - Optional function to run before export.
 * @param {Function} [afterExport] - Optional function to run after export.
 */
const exportImage = async (targetNode, fileName = 'export.png', beforeExport, afterExport) => {
  try {
    if (beforeExport) beforeExport();
    const dataUrl = await htmlToImage.toPng(targetNode);
    const link = document.createElement('a');
    link.download = fileName;
    link.href = dataUrl;
    link.click();
  } catch (error) {
    console.error('Image export failed:', error);
  } finally {
    if (afterExport) afterExport();
  }
};

const ExportImageComponent = ({
  targetNode,
  fileName = 'export.png',
  beforeExport,
  afterExport,
  buttonStyle,
}) => {
  const iconButtonRef = useRef(null);
  const classes = useStyles();

  const handleExport = () => {
    if (!targetNode) return;

    exportImage(
        targetNode,
        fileName,
        () => {
          if (iconButtonRef.current) {
            iconButtonRef.current.style.display = 'none';
          }
          if (beforeExport) beforeExport();
        },
        () => {
          if (iconButtonRef.current) {
            iconButtonRef.current.style.display = '';
          }
          if (afterExport) afterExport();
        },
    );
  };

  return (
    <Tooltip title="Image Export">
      <IconButton
        ref={iconButtonRef}
        className={classes.exportButton}
        onClick={handleExport}
        size="small"
      >
        <DownloadIcon fontSize="small" />
      </IconButton>
    </Tooltip>
  );
};

ExportImageComponent.propTypes = {
  targetNode: PropTypes.instanceOf(HTMLElement),
  fileName: PropTypes.string,
  beforeExport: PropTypes.func,
  afterExport: PropTypes.func,
  buttonStyle: PropTypes.object,
};

export default ExportImageComponent;
