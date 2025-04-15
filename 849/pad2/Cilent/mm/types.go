package mm

import "github.com/golang/protobuf/proto"

type ContactInfo struct {
	// 假设联系人信息包含以下字段
	Wxid       string `protobuf:"bytes,1,opt,name=wxid,proto3" json:"wxid,omitempty"`
	Nickname   string `protobuf:"bytes,2,opt,name=nickname,proto3" json:"nickname,omitempty"`
	RemarkName string `protobuf:"bytes,3,opt,name=remark_name,json=remarkName,proto3" json:"remark_name,omitempty"`
}

type InitTotalContactRequest struct {
	Username                  *string `protobuf:"bytes,1,opt,name=username,proto3" json:"username,omitempty"`
	CurrentWxcontactSeq       *int32  `protobuf:"varint,2,opt,name=current_wxcontact_seq,json=currentWxcontactSeq,proto3" json:"current_wxcontact_seq,omitempty"`
	CurrentChatRoomContactSeq *int32  `protobuf:"varint,3,opt,name=current_chat_room_contact_seq,json=currentChatRoomContactSeq,proto3" json:"current_chat_room_contact_seq,omitempty"`
	Offset                    *int32  `protobuf:"varint,4,opt,name=offset,proto3" json:"offset,omitempty"` // 新增偏移量字段
	Limit                     *int32  `protobuf:"varint,5,opt,name=limit,proto3" json:"limit,omitempty"`   // 新增限制数量字段
}

type InitTotalContactResponse struct {
	Contacts []*ContactInfo `protobuf:"bytes,1,rep,name=contacts,proto3" json:"contacts,omitempty"`
}

func (m *InitTotalContactRequest) Reset()         { *m = InitTotalContactRequest{} }
func (m *InitTotalContactRequest) String() string { return proto.CompactTextString(m) }
func (*InitTotalContactRequest) ProtoMessage()    {}

func (m *InitTotalContactResponse) Reset()         { *m = InitTotalContactResponse{} }
func (m *InitTotalContactResponse) String() string { return proto.CompactTextString(m) }
func (*InitTotalContactResponse) ProtoMessage()    {}
