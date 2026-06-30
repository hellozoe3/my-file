Page({
  data: {
    apiUrl: "http://linan.xyz:8000/detect_img",
    totalNum: 45,
    actualNum: 0,
    absentNum: 0,
    showResult: false,
    resultSuccess: true,
    resultImg: "", // 初始为空字符串，禁止undefined
    historyList: [],
    _tempFilePath: "",
    percentStr: "0.0",
    timer: null
  },

  onShow() {
    const history = wx.getStorageSync("signRecordList") || [];
    this.setData({ historyList: history });
  },

  // 输入应到人数
  inputTotal(e) {
    let num = Number(e.detail.value);
    if (isNaN(num) || num < 0) num = 0;
    this.setData({ totalNum: num });
  },

  // 拍照
  takePhoto() {
    wx.chooseMedia({
      count: 1,
      mediaType: ["image"],
      sourceType: ["camera"],
      success: (res) => {
        const path = res.tempFiles[0].tempFilePath;
        this.setData({ _tempFilePath: path });
        this.submitImage(path);
      },
    });
  },

  // 相册上传
  uploadAlbum() {
    wx.chooseMedia({
      count: 1,
      mediaType: ["image"],
      sourceType: ["album"],
      success: (res) => {
        const path = res.tempFiles[0].tempFilePath;
        this.setData({ _tempFilePath: path });
        this.submitImage(path);
      },
    });
  },

  // 提交识别核心方法
  submitImage(filePath) {
    const that = this;
    this.setData({ showResult: false });

    wx.showLoading({
      title: "AI 正在清点人数...",
      mask: true,
    });

    wx.uploadFile({
      url: that.data.apiUrl,
      filePath: filePath,
      name: "file",
      timeout: 15000, // 超时延长到15秒
      success(res) {
        wx.hideLoading();
        let data;
        // 解析JSON异常捕获
        try {
          data = JSON.parse(res.data);
          console.log("接口返回完整数据：", data);
        } catch (err) {
          wx.showToast({ title: "接口数据解析失败", icon: "none" });
          // 图片强制置空字符串
          that.setData({ resultImg: "" });
          return;
        }

        // 读取识别人数
        const personCount = data.face_count ? data.face_count : (data.targets ? data.targets.length : 0);
        const total = that.data.totalNum;
        const absent = total - personCount;

        // 计算出勤率
        let percent = "0.0";
        if (total > 0) {
          percent = (personCount / total * 100).toFixed(1);
        }

        // ========== 关键修复：判断base64图片是否存在 ==========
        let imgBase64 = data.img_base64 || ""; 

        that.setData({
          actualNum: personCount,
          absentNum: absent < 0 ? 0 : absent,
          resultSuccess: personCount > 0 && imgBase64 !== "",
          showResult: true,
          resultImg: imgBase64, // 空则赋值 ""，不会出现undefined
          percentStr: percent
        });

        // 保存签到记录
        const record = {
          time: new Date().toLocaleString(),
          total: total,
          actual: personCount,
          absent: absent < 0 ? 0 : absent,
          img: imgBase64,
        };
        const newHistory = [record, ...that.data.historyList];
        that.setData({ historyList: newHistory });
        wx.setStorageSync("signRecordList", newHistory);
      },
      fail() {
        wx.hideLoading();
        // 网络失败，图片置空
        that.setData({ resultImg: "" });
        wx.showModal({
          title: "连接失败",
          content: "无法连接到 AI 服务，请检查网络后重试",
          confirmText: "重试",
          cancelText: "取消",
          success: (res) => {
            if (res.confirm && that.data._tempFilePath) {
              that.submitImage(that.data._tempFilePath);
            }
          },
        });
      },
    });
  },

  // 查看大图
  previewImage() {
    if (!this.data.resultImg) return;
    wx.showLoading({ title: "加载中..." });
    const fs = wx.getFileSystemManager();
    const timestamp = Date.now();
    const savedPath = wx.env.USER_DATA_PATH + "/preview_" + timestamp + ".jpg";
    fs.writeFile({
      filePath: savedPath,
      data: this.data.resultImg.replace(/^data:image\/\w+;base64,/, ""),
      encoding: "base64",
      success() {
        wx.hideLoading();
        wx.previewImage({
          urls: [savedPath],
          current: savedPath,
        });
      },
      fail() {
        wx.hideLoading();
        wx.showToast({ title: "预览失败", icon: "none" });
      },
    });
  },

  // 重新识别
  retryRecognition() {
    if (this.data._tempFilePath) {
      this.submitImage(this.data._tempFilePath);
    } else {
      wx.showToast({ title: "请重新拍照或上传", icon: "none" });
    }
  },
});