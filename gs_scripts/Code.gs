// Google Apps Script (Code.gs) - Web App for reading and writing Google Sheet
// Deploy: Deploy -> New deployment -> Web app
// Execute as: Me
// Who has access: Anyone (or Anyone with link) if you want to call it from a public Streamlit app without OAuth
//
// Edit SPREADSHEET_ID and SECRET to match your values.

const SPREADSHEET_ID = 'REPLACE_WITH_SPREADSHEET_ID';
const SHEET_NAME = 'Sheet1';
const SECRET = 'REPLACE_WITH_A_RANDOM_SECRET_STRING';

function _getSheet() {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  let sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME);
    sheet.appendRow(['Timestamp', 'FirstName', 'LastName', 'LineUserId', 'CardId']);
  }
  return sheet;
}

function _readAll() {
  const sheet = _getSheet();
  const data = sheet.getDataRange().getValues();
  if (data.length <= 1) return [];
  const headers = data[0].map(h => String(h || '').trim());
  const rows = data.slice(1);
  const out = rows.map(r => {
    const obj = {};
    for (let i = 0; i < headers.length; i++) {
      obj[headers[i] || ('col' + i)] = r[i];
    }
    return obj;
  });
  return out;
}

function doGet(e) {
  try {
    const params = e.parameter || {};
    if (params.action && params.action === 'read') {
      const rows = _readAll();
      return ContentService
        .createTextOutput(JSON.stringify(rows))
        .setMimeType(ContentService.MimeType.JSON);
    } else {
      return ContentService
        .createTextOutput(JSON.stringify({result:'ok', message: 'Web app ready'}))
        .setMimeType(ContentService.MimeType.JSON);
    }
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({result:'error', message: err.message}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doPost(e) {
  try {
    // Support JSON (application/json) or form encoded / query params
    let payload = {};
    if (e.postData && e.postData.type === 'application/json' && e.postData.contents) {
      payload = JSON.parse(e.postData.contents);
    } else if (e.postData && e.postData.contents) {
      try {
        payload = JSON.parse(e.postData.contents);
      } catch (err) {
        payload = e.parameter || {};
      }
    } else {
      payload = e.parameter || {};
    }

    const action = payload.action || 'write';

    if (action === 'read') {
      const rows = _readAll();
      return ContentService
        .createTextOutput(JSON.stringify(rows))
        .setMimeType(ContentService.MimeType.JSON);
    } else if (action === 'write') {
      if (!payload.secret || payload.secret !== SECRET) {
        return ContentService
          .createTextOutput(JSON.stringify({result:'error', message:'unauthorized'}))
          .setMimeType(ContentService.MimeType.JSON);
      }

      const fname = payload.fname || payload.firstName || '';
      const lname = payload.lname || payload.lastName || '';
      const line_id = payload.line_id || payload.lineUserId || '';
      const card_id = payload.card_id || payload.cardId || '';

      const sheet = _getSheet();
      const ts = new Date();
      sheet.appendRow([ts, fname, lname, line_id, card_id]);

      return ContentService
        .createTextOutput(JSON.stringify({result:'ok'}))
        .setMimeType(ContentService.MimeType.JSON);
    } else {
      return ContentService
        .createTextOutput(JSON.stringify({result:'error', message:'unknown action'}))
        .setMimeType(ContentService.MimeType.JSON);
    }
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({result:'error', message: err.message}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
