package Friend

import (
	"fmt"
	"github.com/golang/protobuf/proto"
	"wechatdll/Algorithm"
	"wechatdll/Cilent/mm"
	"wechatdll/comm"
	"wechatdll/models"
)

type GetContactListParams struct {
	Wxid                      string
	CurrentWxcontactSeq       int32
	CurrentChatRoomContactSeq int32
	Offset                    int32 // 偏移量参数
	Limit                     int32 // 限制数量参数
}

func GetTotalContractList(Data GetContactListParams) models.ResponseResult {
	var allContacts []*mm.ContactInfo // 使用指针切片来存储所有联系人的切片

	for {
		D, err := comm.GetLoginata(Data.Wxid)
		if err != nil {
			return models.ResponseResult{
				Code:    -8,
				Success: false,
				Message: fmt.Sprintf("异常：%v", err.Error()),
				Data:    nil,
			}
		}

		req := &mm.InitTotalContactRequest{
			Username:                  proto.String(Data.Wxid),
			CurrentWxcontactSeq:       proto.Int32(Data.CurrentWxcontactSeq),
			CurrentChatRoomContactSeq: proto.Int32(Data.CurrentChatRoomContactSeq),
			Offset:                    proto.Int32(Data.Offset), // 设置偏移量
			Limit:                     proto.Int32(Data.Limit),  // 设置限制数量
		}

		reqdata, err := proto.Marshal(req)
		if err != nil {
			return models.ResponseResult{
				Code:    -8,
				Success: false,
				Message: fmt.Sprintf("系统异常：%v", err.Error()),
				Data:    nil,
			}
		}

		// 发包
		protobufdata, _, errtype, err := comm.SendRequest(comm.SendPostData{
			Ip:     D.Mmtlsip,
			Host:   D.MmtlsHost,
			Cgiurl: "/cgi-bin/micromsg-bin/initcontact",
			Proxy:  D.Proxy,
			PackData: Algorithm.PackData{
				Reqdata:          reqdata,
				Cgi:              851,
				Uin:              D.Uin,
				Cookie:           D.Cooike,
				Sessionkey:       D.Sessionkey,
				EncryptType:      5,
				Loginecdhkey:     D.RsaPublicKey,
				Clientsessionkey: D.Clientsessionkey,
				UseCompress:      false,
			},
		}, D.MmtlsKey)

		if err != nil {
			return models.ResponseResult{
				Code:    errtype,
				Success: false,
				Message: err.Error(),
				Data:    nil,
			}
		}

		// 解包
		Response := mm.InitTotalContactResponse{}
		err = proto.Unmarshal(protobufdata, &Response)
		if err != nil {
			return models.ResponseResult{
				Code:    -8,
				Success: false,
				Message: fmt.Sprintf("反序列化失败：%v", err.Error()),
				Data:    nil,
			}
		}

		// 将本次获取的联系人添加到allContacts切片中
		allContacts = append(allContacts, Response.Contacts...)

		// 检查是否有更多联系人
		if len(Response.Contacts) < int(Data.Limit) {
			break
		}

		// 更新偏移量以获取下一页联系人
		Data.Offset += Data.Limit
	}

	return models.ResponseResult{
		Code:    0,
		Success: true,
		Message: "成功",
		Data:    allContacts,
	}
}
