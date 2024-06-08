var getIds = function() {
	let list = document.getElementsByClassName("listview-cleartext")
	let result = []
	for (var i = 0; i < list.length; i++) {
		let substr = list[i].href.substr(list[i].href.indexOf("=")+1)
		let idstr = substr.substr(0,substr.indexOf('/'))
		 result.push({
		 	"name": list[i].innerHTML,
		 	"entry" : parseInt(idstr)
		 })
	}
	console.log((result))
	console.log(result.map(i=>i.entry))
}